#!/usr/bin/env python3
"""Compile the skill's code snippets against the latest published HyperTrack SDKs.

- ```swift  -> swiftc -typecheck against HyperTrack.xcframework (iOS simulator slice)   [needs Xcode]
- ```kotlin -> kotlinc against sdk-android + plugin jars and android.jar                [needs a JDK + Android SDK]
- ```ts     -> tsc against the published hypertrack-sdk-react-native /
               hypertrack-sdk-ionic-capacitor type declarations                          [needs node/npx]
- ```dart   -> dart analyze against the published hypertrack_plugin (pub.dev),
               with a stub for package:flutter/services.dart                            [downloads the Dart SDK]
- ```csharp -> dotnet build against HyperTrackSdkMaui.dll from the NuGet package          [downloads the .NET SDK]

Blocks whose fence info contains `no-check` are skipped.
A missing toolchain fails the check; use --only to check a subset of languages.
Downloads are cached in .cache/snippets/. Override versions with HT_IOS_VERSION, HT_ANDROID_VERSION,
HT_RN_VERSION, HT_IONIC_VERSION, HT_FLUTTER_VERSION, HT_MAUI_VERSION.

Usage: python3 tools/check_snippets.py [--only swift|kotlin|ts|dart|csharp]
"""

import argparse
import glob
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache" / "snippets"
REFS = sorted((ROOT / "skills").glob("**/*.md"))
FENCE_RE = re.compile(r"^```(\w+)([^\n]*)\n(.*?)^```", re.M | re.S)
MAVEN = "https://s3-us-west-2.amazonaws.com/m2.hypertrack.com/com/hypertrack"
KOTLIN_VERSION = "2.1.21"


def log(message):
    print(message, flush=True)


def download(url, dest):
    dest = Path(dest)
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "hypertrack-skills-check/1.0"})
    with urllib.request.urlopen(request, timeout=300) as response, open(tmp, "wb") as out:
        shutil.copyfileobj(response, out)
    tmp.rename(dest)
    return dest


def latest(repo, env):
    if os.environ.get(env):
        return os.environ[env]
    url = f"https://api.github.com/repos/hypertrack/{repo}/releases/latest"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"}), timeout=20) as r:
        return json.load(r)["tag_name"]


def blocks(language):
    found = []
    for ref in REFS:
        for lang, info, body in FENCE_RE.findall(ref.read_text()):
            if lang == language and "no-check" not in info:
                found.append((ref.relative_to(ROOT), body))
    return found


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def failure_text(proc, diagnostics=None):
    """Error text for a compiler run, or "" on success. A nonzero exit always fails."""
    if proc.returncode == 0:
        return ""
    text = (diagnostics or proc.stderr or proc.stdout or "").strip()
    return text or f"compiler exited with status {proc.returncode} and no output"


def missing_toolchain(language, count, reason):
    """A language we can't check counts as failing, so a broken setup can't look green."""
    log(f"FAIL {language}: {count} block(s) not checked, {reason} (use --only to check other languages)")
    return count


def report(language, results):
    failed = [r for r in results if r[2]]
    for path, index, error in results:
        status = "FAIL" if error else "ok  "
        log(f"{status} {language} block {index} in {path}")
        if error:
            log("     " + error.strip().replace("\n", "\n     ")[:4000])
    return len(failed)


def check_swift():
    snippets = blocks("swift")
    if not snippets:
        return 0
    if not shutil.which("xcrun"):
        return missing_toolchain("swift", len(snippets), "Xcode (xcrun) not found")
    version = latest("sdk-ios", "HT_IOS_VERSION")
    base = CACHE / f"ios-{version}"
    framework = base / "HyperTrack.xcframework"
    if not framework.exists():
        archive = download(f"https://github.com/hypertrack/sdk-ios/releases/download/{version}/HyperTrack.xcframework.zip", base / "sdk.zip")
        zipfile.ZipFile(archive).extractall(base)
    slice_dir = next(framework.glob("ios-*-simulator"))
    sdk = run(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"]).stdout.strip()
    log(f"swift: {len(snippets)} blocks against HyperTrack iOS {version}")
    results = []
    work = CACHE / "work-swift"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    for index, (path, body) in enumerate(snippets):
        source = work / f"block{index}.swift"
        source.write_text(body)
        out = run(["xcrun", "swiftc", "-typecheck", "-parse-as-library", "-target", "arm64-apple-ios15.0-simulator",
                   "-sdk", sdk, "-F", str(slice_dir), str(source)])
        results.append((path, index, failure_text(out)))
    return report("swift", results)


def java_home():
    candidates = [os.environ.get("JAVA_HOME"), "/Applications/Android Studio.app/Contents/jbr/Contents/Home"]
    for candidate in candidates:
        if candidate and Path(candidate, "bin", "java").exists():
            return candidate
    return None


def android_jar():
    roots = [os.environ.get("ANDROID_HOME"), os.environ.get("ANDROID_SDK_ROOT"),
             "/opt/homebrew/share/android-commandlinetools", str(Path.home() / "Library/Android/sdk")]
    jars = []
    for root in filter(None, roots):
        jars += glob.glob(os.path.join(root, "platforms", "android-*", "android.jar"))
    return max(jars, key=lambda j: int(re.search(r"android-(\d+)", j).group(1)), default=None)


def hypertrack_jars(version):
    base = CACHE / f"android-{version}"
    pom = download(f"{MAVEN}/sdk-android/{version}/sdk-android-{version}.pom", base / "sdk-android.pom").read_text()
    artifacts = ["sdk-android"] + re.findall(r"<groupId>com\.hypertrack</groupId>\s*<artifactId>([^<]+)</artifactId>", pom)
    jars = []
    for artifact in dict.fromkeys(artifacts):
        jar = base / f"{artifact}.jar"
        if not jar.exists():
            try:
                download(f"{MAVEN}/{artifact}/{version}/{artifact}-{version}.jar", jar)
                if not zipfile.is_zipfile(jar):
                    raise ValueError
            except Exception:
                jar.unlink(missing_ok=True)
                aar = download(f"{MAVEN}/{artifact}/{version}/{artifact}-{version}.aar", base / f"{artifact}.aar")
                with zipfile.ZipFile(aar) as z, open(jar, "wb") as out:
                    out.write(z.read("classes.jar"))
        jars.append(str(jar))
    return jars


def check_kotlin():
    snippets = blocks("kotlin")
    if not snippets:
        return 0
    home, platform_jar = java_home(), android_jar()
    if not home or not platform_jar:
        return missing_toolchain(
            "kotlin", len(snippets), f"JDK ({home or 'missing'}) or android.jar ({platform_jar or 'missing'}) not found"
        )
    kotlinc = CACHE / f"kotlinc-{KOTLIN_VERSION}" / "kotlinc" / "bin" / "kotlinc"
    if not kotlinc.exists():
        archive = download(f"https://github.com/JetBrains/kotlin/releases/download/v{KOTLIN_VERSION}/kotlin-compiler-{KOTLIN_VERSION}.zip",
                           CACHE / f"kotlin-compiler-{KOTLIN_VERSION}.zip")
        zipfile.ZipFile(archive).extractall(kotlinc.parents[2])
        kotlinc.chmod(0o755)
        (kotlinc.parent / "kotlin").chmod(0o755)
    version = latest("sdk-android", "HT_ANDROID_VERSION")
    classpath = os.pathsep.join(hypertrack_jars(version) + [platform_jar])
    log(f"kotlin: {len(snippets)} blocks against HyperTrack Android {version}")
    work = CACHE / "work-kotlin"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    results = []
    env = dict(os.environ, JAVA_HOME=home)
    for index, (path, body) in enumerate(snippets):
        source = work / f"block{index}.kt"
        source.write_text(f"package snippet{index}\n\n{body}")
        out = run([str(kotlinc), "-nowarn", "-cp", classpath, str(source), "-d", str(work / f"out{index}")], env=env)
        errors = "\n".join(line for line in out.stderr.splitlines() if "error:" in line or line.startswith(" "))
        results.append((path, index, failure_text(out, errors)))
    return report("kotlin", results)


def npm_package(name, version, dest):
    target = dest / "node_modules" / name
    if target.exists():
        return
    tarball = run(["npm", "pack", "-s", f"{name}@{version}"], cwd=dest).stdout.strip().splitlines()[-1]
    with tarfile.open(dest / tarball) as archive:
        archive.extractall(dest / "unpacked")
    shutil.move(str(dest / "unpacked" / "package"), str(target))


STUBS = {
    "react-native": "export interface EmitterSubscription { remove(): void }\n"
    "export const NativeModules: any;\nexport const Platform: any;\n"
    "export class NativeEventEmitter { constructor(m?: any); addListener(e: string, l: (...a: any[]) => any): EmitterSubscription }\n",
    "@capacitor/core": "export declare function registerPlugin<T>(name: string, impl?: any): T;\n"
    "export interface PluginListenerHandle { remove(): Promise<void> }\n",
}


def check_ts():
    snippets = blocks("ts")
    if not snippets:
        return 0
    if not shutil.which("npm") or not shutil.which("npx"):
        return missing_toolchain("ts", len(snippets), "npm/npx not found")
    rn = latest("sdk-react-native", "HT_RN_VERSION")
    ionic = latest("sdk-ionic-capacitor", "HT_IONIC_VERSION")
    work = CACHE / f"ts-rn{rn}-ionic{ionic}"
    (work / "node_modules").mkdir(parents=True, exist_ok=True)
    npm_package("hypertrack-sdk-react-native", rn, work)
    npm_package("hypertrack-sdk-ionic-capacitor", ionic, work)
    for module, stub in STUBS.items():
        directory = work / "node_modules" / module
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "index.d.ts").write_text(stub)
        (directory / "package.json").write_text(json.dumps({"name": module, "types": "index.d.ts"}))
    log(f"ts: {len(snippets)} blocks against hypertrack-sdk-react-native {rn}, hypertrack-sdk-ionic-capacitor {ionic}")
    results = []
    for index, (path, body) in enumerate(snippets):
        for old in work.glob("block*.ts"):
            old.unlink()
        (work / f"block{index}.ts").write_text(body)
        (work / "tsconfig.json").write_text(json.dumps({
            "compilerOptions": {"strict": True, "noEmit": True, "target": "ES2020", "module": "ESNext",
                                "moduleResolution": "Bundler", "lib": ["ES2020", "DOM"], "esModuleInterop": True},
            "include": [f"block{index}.ts"],
        }))
        out = run(["npx", "-y", "-p", "typescript@5", "tsc", "-p", "tsconfig.json"], cwd=work)
        results.append((path, index, failure_text(out, out.stdout + out.stderr)))
    return report("ts", results)


def platform_names():
    system = {"Darwin": "macos", "Linux": "linux"}.get(platform.system())
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "AMD64": "x64"}.get(platform.machine())
    return system, arch


FLUTTER_SERVICES_STUB = """
class MethodChannel {
  const MethodChannel(String name);
  Future<T?> invokeMethod<T>(String method, [dynamic arguments]) async => null;
}

class EventChannel {
  const EventChannel(String name);
  Stream<dynamic> receiveBroadcastStream([dynamic arguments]) => const Stream.empty();
}
"""


def check_dart():
    snippets = blocks("dart")
    if not snippets:
        return 0
    system, arch = platform_names()
    if not system or not arch:
        return missing_toolchain("dart", len(snippets), f"no Dart SDK build for {platform.system()} {platform.machine()}")
    with urllib.request.urlopen("https://storage.googleapis.com/dart-archive/channels/stable/release/latest/VERSION", timeout=20) as r:
        dart_version = json.load(r)["version"]
    sdk = CACHE / f"dart-{dart_version}"
    dart = sdk / "dart-sdk" / "bin" / "dart"
    if not dart.exists():
        archive = download(
            f"https://storage.googleapis.com/dart-archive/channels/stable/release/{dart_version}/sdk/dartsdk-{system}-{arch}-release.zip",
            CACHE / f"dartsdk-{dart_version}.zip",
        )
        run(["unzip", "-q", "-o", str(archive), "-d", str(sdk)])
    version = os.environ.get("HT_FLUTTER_VERSION")
    if not version:
        with urllib.request.urlopen("https://pub.dev/api/packages/hypertrack_plugin", timeout=20) as r:
            version = json.load(r)["latest"]["version"]
    plugin = CACHE / f"hypertrack_plugin-{version}"
    if not (plugin / "lib").exists():
        archive = download(f"https://pub.dev/api/archives/hypertrack_plugin-{version}.tar.gz", CACHE / f"hypertrack_plugin-{version}.tar.gz")
        plugin.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive) as tar:
            tar.extractall(plugin)
    stub = CACHE / "flutter-stub"
    (stub / "lib").mkdir(parents=True, exist_ok=True)
    (stub / "lib" / "services.dart").write_text(FLUTTER_SERVICES_STUB)
    work = CACHE / "work-dart"
    shutil.rmtree(work, ignore_errors=True)
    (work / ".dart_tool").mkdir(parents=True)
    (work / "pubspec.yaml").write_text("name: snippets\nenvironment:\n  sdk: ^3.0.0\n")
    packages = [
        {"name": "hypertrack_plugin", "rootUri": plugin.as_uri(), "packageUri": "lib/", "languageVersion": "3.0"},
        {"name": "flutter", "rootUri": stub.as_uri(), "packageUri": "lib/", "languageVersion": "3.0"},
        {"name": "snippets", "rootUri": "../", "packageUri": "lib/", "languageVersion": "3.0"},
    ]
    (work / ".dart_tool" / "package_config.json").write_text(json.dumps({"configVersion": 2, "packages": packages}))
    log(f"dart: {len(snippets)} blocks against hypertrack_plugin {version} (Dart {dart_version})")
    results = []
    for index, (path, body) in enumerate(snippets):
        source = work / f"block{index}.dart"
        source.write_text(body)
        out = run([str(dart), "analyze", "--fatal-warnings", str(source)], cwd=work)
        results.append((path, index, failure_text(out, out.stdout + out.stderr)))
    return report("dart", results)


def check_csharp():
    snippets = blocks("csharp")
    if not snippets:
        return 0
    dotnet_dir = CACHE / "dotnet"
    dotnet = dotnet_dir / "dotnet"
    if not dotnet.exists():
        installer = download("https://dot.net/v1/dotnet-install.sh", CACHE / "dotnet-install.sh")
        out = run(["bash", str(installer), "--channel", "10.0", "--install-dir", str(dotnet_dir), "--no-path"])
        if out.returncode:
            return missing_toolchain("csharp", len(snippets), f".NET SDK install failed: {out.stderr.strip()[-300:]}")
    version = os.environ.get("HT_MAUI_VERSION")
    if not version:
        with urllib.request.urlopen("https://api.nuget.org/v3-flatcontainer/hypertrack.sdk.maui/index.json", timeout=20) as r:
            version = json.load(r)["versions"][-1]
    package = CACHE / f"maui-{version}"
    if not package.exists():
        archive = download(
            f"https://api.nuget.org/v3-flatcontainer/hypertrack.sdk.maui/{version}/hypertrack.sdk.maui.{version}.nupkg",
            CACHE / f"hypertrack.sdk.maui.{version}.nupkg",
        )
        zipfile.ZipFile(archive).extractall(package)
    assembly = next(package.glob("lib/*android*/HyperTrackSdkMaui.dll"))
    log(f"csharp: {len(snippets)} blocks against HyperTrack.SDK.MAUI {version} ({assembly.parent.name})")
    env = dict(os.environ, DOTNET_ROOT=str(dotnet_dir), DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1")
    results = []
    for index, (path, body) in enumerate(snippets):
        work = CACHE / f"work-csharp-{index}"
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        (work / "Snippet.cs").write_text(body)
        # Plain net10.0 library referencing the Android build of the wrapper: enough to resolve names and signatures.
        (work / "Snippet.csproj").write_text(f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>
  <ItemGroup>
    <Reference Include="HyperTrackSdkMaui"><HintPath>{assembly}</HintPath></Reference>
  </ItemGroup>
</Project>
""")
        out = run([str(dotnet), "build", "-nologo", "-v", "q", "-clp:ErrorsOnly"], cwd=work, env=env)
        errors = "\n".join(line for line in out.stdout.splitlines() if ": error " in line)
        results.append((path, index, failure_text(out, errors)))
    return report("csharp", results)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", choices=["swift", "kotlin", "ts", "dart", "csharp"])
    args = parser.parse_args()
    checks = {"swift": check_swift, "kotlin": check_kotlin, "ts": check_ts, "dart": check_dart, "csharp": check_csharp}
    failures = sum(check() for name, check in checks.items() if not args.only or args.only == name)
    log(f"{failures} failing block(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
