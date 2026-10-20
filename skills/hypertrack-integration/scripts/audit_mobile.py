#!/usr/bin/env python3
"""Static audit of a mobile app's HyperTrack setup (Python 3.9+, stdlib only).

Usage: python3 audit_mobile.py [repo-root] [--check-latest]

Detects iOS, Android, React Native, Expo, Flutter, Ionic Capacitor, and .NET MAUI projects and
reports FAIL (integration will not work), WARN (likely problem or needs a human check), and
PASS lines. Exit code 1 when any FAIL is found. Heuristic: it reads files, it does not build.
"""

import argparse
import json
import os
import plistlib
import re
import sys
import urllib.request

SKIP_DIRS = {
    ".git", "node_modules", "Pods", "build", ".build", "DerivedData", ".gradle", ".dart_tool", ".expo",
    "bin", "obj", ".idea", ".vscode", "vendor", ".symlinks", "Carthage", ".next", "dist", "coverage",
}
CODE_EXTS = {".swift", ".m", ".mm", ".kt", ".java", ".js", ".jsx", ".ts", ".tsx", ".dart", ".cs"}
# Location(<number>, <number>) with optional latitude/longitude names (Kotlin `=`, Swift/C#/Dart `:`).
LOCATION_LITERAL_RE = re.compile(
    r"\bLocation\(\s*(latitude\s*[:=]\s*)?(-?\d+(?:\.\d+)?)\s*,\s*(?:longitude\s*[:=]\s*)?-?\d+(?:\.\d+)?\s*\)"
)
POSITIONAL_LOCATION_RE = re.compile(r"HyperTrack\.Location\(\s*(?!latitude\b)[^)\s]")
RN_CORE = "hypertrack-sdk-react-native"
RN_PLUGIN = "hypertrack-sdk-react-native-plugin-android-"
LATEST_REPO = {
    "ios": "sdk-ios", "android": "sdk-android", "react-native": "sdk-react-native", "expo": "sdk-expo",
    "flutter": "sdk-flutter", "ionic": "sdk-ionic-capacitor",
}


class Report:
    def __init__(self, root):
        self.root = root
        self.lines = []

    def add(self, level, area, message, path=None):
        where = f"  ({os.path.relpath(path, self.root)})" if path else ""
        self.lines.append((level, area, message + where))

    def fail(self, area, message, path=None):
        self.add("FAIL", area, message, path)

    def warn(self, area, message, path=None):
        self.add("WARN", area, message, path)

    def ok(self, area, message, path=None):
        self.add("PASS", area, message, path)


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.endswith(".xcframework")]
        for name in filenames:
            yield os.path.join(dirpath, name)


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def strip_version(value):
    return re.sub(r"^[\^~>=<\s]+", "", str(value or "")).strip()


def load_plist(path):
    try:
        with open(path, "rb") as handle:
            data = plistlib.load(handle)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def placeholder(value):
    text = str(value or "").strip()
    return not text or bool(re.search(r"(?i)your|paste|<|put-your|publishable_key_here|xxx", text))


def audit(root):
    report = Report(root)
    files = list(walk(root))
    by_name = {}
    for path in files:
        by_name.setdefault(os.path.basename(path), []).append(path)

    detected = {}

    # ---- package.json based: React Native, Expo, Ionic -------------------------------------
    for path in by_name.get("package.json", []):
        try:
            pkg = json.loads(read(path))
        except ValueError:
            continue
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        if "hypertrack-sdk-expo" in deps:
            detected["expo"] = strip_version(deps["hypertrack-sdk-expo"])
        if RN_CORE in deps:
            detected["react-native"] = strip_version(deps[RN_CORE])
            audit_rn_packages(report, path, deps)
        if "hypertrack-sdk-ionic-capacitor" in deps:
            detected["ionic"] = strip_version(deps["hypertrack-sdk-ionic-capacitor"])

    # ---- Flutter -------------------------------------------------------------------------------
    flutter_firebase = False
    for path in by_name.get("pubspec.yaml", []):
        text = read(path)
        match = re.search(r"^\s*hypertrack_plugin:\s*(\S+)?", text, re.M)
        if match:
            detected["flutter"] = strip_version(match.group(1) or "?")
            flutter_firebase = bool(re.search(r"^\s*firebase_messaging:", text, re.M))

    # ---- .NET MAUI -----------------------------------------------------------------------------
    for path in files:
        if not path.endswith(".csproj"):
            continue
        text = read(path)
        match = re.search(r'Include="HyperTrack\.SDK\.MAUI"\s+Version="([^"]+)"', text, re.I)
        if not match:
            continue
        detected["maui"] = match.group(1)
        if "sdk-android-model" not in text:
            report.warn("maui", "AndroidMavenLibrary workaround for sdk-android-model missing (see cross-platform.md)", path)
        frameworks = set(re.findall(r"net\d+\.\d+-android", " ".join(re.findall(r"<TargetFrameworks?>([^<]*)<", text))))
        conditions = set(re.findall(r"sdk-android-model[^>]*'(net\d+\.\d+-android)'", text))
        if frameworks and conditions and not conditions & frameworks:
            report.fail("maui", f"workaround Condition targets {sorted(conditions)} but the project targets {sorted(frameworks)}: it never applies", path)
        if "GoogleServicesJson" not in text:
            report.warn("maui", "no <GoogleServicesJson> item: FCM on Android needs google-services.json", path)

    # ---- Expo config ---------------------------------------------------------------------------
    if "expo" in detected:
        audit_expo(report, by_name, files)

    # ---- Native iOS ----------------------------------------------------------------------------
    pod_or_spm = None
    for path in by_name.get("Podfile.lock", []) + by_name.get("Podfile", []):
        match = re.search(r"-\s*HyperTrack \(([\d.]+)\)", read(path)) or re.search(
            r"pod\s+['\"]HyperTrack['\"](?:\s*,\s*['\"]([^'\"]+))?", read(path)
        )
        if match:
            pod_or_spm = match.group(1) or "?"
            break
    for path in files:
        if path.endswith("project.pbxproj") and "github.com/hypertrack/sdk-ios" in read(path):
            pod_or_spm = pod_or_spm or "SPM"
    if pod_or_spm:
        detected["ios"] = pod_or_spm
    has_ios_project = any(p.endswith(("project.pbxproj", "/Info.plist")) for p in files)
    if detected and has_ios_project:
        audit_ios(report, by_name, files, flutter_firebase)

    # ---- Native Android ------------------------------------------------------------------------
    gradle_files = [p for p in files if re.search(r"\.gradle(\.kts)?$", p)]
    gradle_text = {p: read(p) for p in gradle_files}
    artifacts = {}
    for text in gradle_text.values():
        for artifact, version in re.findall(r"com\.hypertrack:([a-z0-9-]+):([\w.$\-{}]+)", text):
            artifacts.setdefault(artifact, set()).add(version)
    if "sdk-android" in artifacts:
        detected["android"] = "/".join(sorted(artifacts["sdk-android"]))
    has_android_project = bool(gradle_files) or "AndroidManifest.xml" in by_name
    if detected and has_android_project:
        audit_android(report, by_name, files, gradle_text, artifacts, detected)

    # ---- Code-level checks ---------------------------------------------------------------------
    if detected:
        audit_code(report, files)

    return report, detected


def audit_rn_packages(report, path, deps):
    versions = {name: strip_version(v) for name, v in deps.items() if name == RN_CORE or name.startswith(RN_PLUGIN)}
    plugins = [n for n in versions if n.startswith(RN_PLUGIN)]
    if not any("location-services-google" in n for n in plugins):
        report.fail("react-native", f"missing {RN_PLUGIN}location-services-google (required on Android)", path)
    if not any("push-service-firebase" in n for n in plugins):
        report.fail("react-native", f"missing {RN_PLUGIN}push-service-firebase (required on Android)", path)
    if len(set(versions.values())) > 1:
        report.fail("react-native", f"HyperTrack package versions differ: {versions}", path)
    else:
        report.ok("react-native", f"HyperTrack packages aligned at {versions.get(RN_CORE)}", path)


def audit_expo(report, by_name, files):
    configs = [p for p in files if re.search(r"(^|/)app\.(json|config\.(js|ts|mjs|cjs|json))$", p)]
    text = "\n".join(read(p) for p in configs)
    path = configs[0] if configs else None
    if "hypertrack-sdk-expo" not in text:
        report.fail("expo", "hypertrack-sdk-expo is not in the app config plugins", path)
        return
    for key, level in (("publishableKey", "fail"), ("locationPermission", "fail"), ("motionPermission", "warn")):
        if key not in text:
            getattr(report, level)("expo", f"plugin param {key} not set", path)
    if "googleServicesFile" not in text:
        report.warn("expo", "android.googleServicesFile not set: FCM (silent push) needs google-services.json", path)
    if "aps-environment" not in text and "expo-notifications" not in text:
        report.warn("expo", "no iOS push entitlement found (aps-environment / expo-notifications): check Push capability", path)


def audit_ios(report, by_name, files, flutter_firebase):
    pbx = "\n".join(read(p) for p in files if p.endswith("project.pbxproj"))
    plists = []
    for path in by_name.get("Info.plist", []):
        if re.search(r"(?i)/(tests?|uitests|[^/]*tests)/|/Pods/|\.bundle/|\.framework/", path):
            continue
        data = load_plist(path)
        if data is None or "NSExtension" in data:
            continue
        if any(k in data for k in ("CFBundleExecutable", "UILaunchStoryboardName", "LSRequiresIPhoneOS",
                                   "UIApplicationSceneManifest", "HyperTrackPublishableKey")):
            plists.append((path, data))
    if not plists:
        report.warn("ios", "no app Info.plist found (generated Info.plist? check build settings manually)")
        return

    def has_key(data, key):
        return key in data or f"INFOPLIST_KEY_{key}" in pbx

    for path, data in plists:
        key = data.get("HyperTrackPublishableKey")
        if key is None:
            report.fail("ios", "HyperTrackPublishableKey missing from Info.plist", path)
        elif placeholder(key):
            report.warn("ios", f"HyperTrackPublishableKey looks like a placeholder: {key!r}", path)
        else:
            report.ok("ios", "HyperTrackPublishableKey set", path)
        for purpose in ("NSLocationWhenInUseUsageDescription", "NSLocationAlwaysAndWhenInUseUsageDescription"):
            if not has_key(data, purpose):
                report.fail("ios", f"{purpose} missing (required purpose string)", path)
            elif purpose in data and placeholder(data[purpose]):
                report.warn("ios", f"{purpose} looks like a placeholder: write it for the worker", path)
        if not has_key(data, "NSMotionUsageDescription"):
            report.warn("ios", "NSMotionUsageDescription missing (optional; improves activity detection)", path)
        modes = data.get("UIBackgroundModes") or []
        for mode in ("location", "remote-notification"):
            if mode not in modes:
                report.fail("ios", f"UIBackgroundModes missing '{mode}'", path)
        if data.get("HyperTrackSwizzlingEnabled") is False:
            code = "\n".join(read(p) for p in files if p.endswith((".swift", ".m", ".mm")))
            if "didRegisterForRemoteNotificationsWithDeviceToken" not in code or "HyperTrack.did" not in code:
                report.fail("ios", "swizzling disabled but AppDelegate doesn't forward push callbacks to HyperTrack", path)
            else:
                report.ok("ios", "swizzling disabled and AppDelegate forwards calls", path)
        elif flutter_firebase:
            report.warn("ios", "Flutter app uses firebase_messaging: set HyperTrackSwizzlingEnabled=NO and forward AppDelegate calls", path)

    entitlements = [p for p in files if p.endswith(".entitlements") or os.path.basename(p) == "Entitlements.plist"]
    if any("aps-environment" in read(p) for p in entitlements):
        report.ok("ios", "Push Notifications entitlement (aps-environment) present")
    else:
        report.fail("ios", "no aps-environment entitlement: add the Push Notifications capability")
    report.warn("ios", "manual: APNs .p8 key + Team ID uploaded on the HyperTrack dashboard Setup page")


def publishable_key_values(manifest):
    """android:value (or android:resource) of each HyperTrackPublishableKey <meta-data>, in any attribute order."""
    values = []
    for tag in re.findall(r"<meta-data\b[^>]*>", manifest):
        if re.search(r'android:name\s*=\s*"HyperTrackPublishableKey"', tag):
            match = re.search(r'android:(?:value|resource)\s*=\s*"([^"]*)"', tag)
            values.append(match.group(1) if match else "")
    return values


def audit_android(report, by_name, files, gradle_text, artifacts, detected):
    manifests = [p for p in by_name.get("AndroidManifest.xml", []) if "/src/main/" in p or "/Platforms/Android/" in p]
    manifests = manifests or by_name.get("AndroidManifest.xml", [])
    key_found = False
    for path in manifests:
        for value in publishable_key_values(read(path)):
            key_found = True
            if placeholder(value):
                report.warn("android", f"HyperTrackPublishableKey looks like a placeholder: {value!r}", path)
            else:
                report.ok("android", "HyperTrackPublishableKey meta-data set", path)
    if not key_found and "expo" not in detected:
        report.fail("android", "HyperTrackPublishableKey <meta-data> missing from AndroidManifest.xml",
                     manifests[0] if manifests else None)

    native = "sdk-android" in artifacts
    if native:
        if not ({"location-services-google", "location-services-google-19-0-1"} & artifacts.keys()):
            report.fail("android", "missing com.hypertrack:location-services-google (required plugin)")
        if "push-service-firebase" not in artifacts:
            report.fail("android", "missing com.hypertrack:push-service-firebase (required plugin)")
        versions = set().union(*artifacts.values())
        if len(versions) > 1:
            report.fail("android", f"HyperTrack artifacts use different versions: {sorted(versions)}")
        else:
            report.ok("android", f"HyperTrack artifacts aligned at {versions.pop()}")

    all_gradle = "\n".join(gradle_text.values())
    bundles_repo = any(k in detected for k in ("flutter", "ionic", "maui", "expo"))
    if "m2.hypertrack.com" in all_gradle:
        report.ok("android", "HyperTrack Maven repository declared")
    elif not bundles_repo:
        report.fail("android", "HyperTrack Maven repo (https://s3-us-west-2.amazonaws.com/m2.hypertrack.com/) not declared")
    elif "FAIL_ON_PROJECT_REPOS" in all_gradle:
        report.warn("android", "settings enforce FAIL_ON_PROJECT_REPOS: add the HyperTrack Maven repo to settings.gradle")

    pinned = re.findall(r"play-services-location:([\d.]+)", all_gradle)
    if any(tuple(int(x) for x in v.split(".")[:2]) < (20, 0) for v in pinned if re.match(r"^\d+\.\d+", v)):
        report.warn("android", f"play-services-location pinned to {pinned}: use location-services-google-19-0-1")

    google_services = by_name.get("google-services.json", [])
    if google_services:
        report.ok("android", "google-services.json present", google_services[0])
        if "com.google.gms.google-services" not in all_gradle and "expo" not in detected and "maui" not in detected:
            report.warn("android", "google-services Gradle plugin (com.google.gms.google-services) not applied")
    elif "expo" not in detected:
        report.fail("android", "google-services.json not found: Firebase/FCM is required for silent push")
    report.warn("android", "manual: FCM service-account JSON uploaded on the HyperTrack dashboard Setup page")


def audit_code(report, files):
    code_files = [p for p in files if os.path.splitext(p)[1] in CODE_EXTS]
    set_re = re.compile(r"HyperTrack\.(workerHandle\s*=|setWorkerHandle\s*\(|WorkerHandle\s*=)")
    clear_re = re.compile(r"HyperTrack\.(workerHandle\s*=|setWorkerHandle\s*\(|WorkerHandle\s*=)\s*(\"\"|'')")
    found_set = found_clear = found_errors = False
    for path in code_files:
        text = read(path)
        if re.search(r"HYPERTRACK_SECRET_KEY|v3\.api\.hypertrack\.com|[\"']SecretKey[\"']", text):
            report.warn("code", "mobile code references the HyperTrack backend API or SecretKey: secrets must stay server-side", path)
        if "hypertrack" not in text.lower():
            continue
        ext = os.path.splitext(path)[1]
        found_set |= bool(set_re.search(text))
        found_clear |= bool(clear_re.search(text))
        found_errors |= bool(re.search(r"subscribeToErrors|errorsSubscription|SubscribeToErrors|getErrors\(|HyperTrack\.errors|HyperTrack\.Errors", text))
        if ext == ".dart" and re.search(r"HyperTrack\.workerHandle\s*=", text):
            report.fail("code", "Flutter: HyperTrack.workerHandle has no setter, use HyperTrack.setWorkerHandle(...)", path)
        if ext == ".cs" and re.search(r"HyperTrack\.Set(WorkerHandle|Name|Metadata)\s*\(", text):
            report.fail("code", "MAUI: use the WorkerHandle / Name / Metadata properties, not Set*() methods", path)
        if ext == ".swift" and ".location(.permissions(" in text:
            report.fail("code", "Swift: error pattern is .permissions(.location(...)), not .location(.permissions(...))", path)
        if re.search(r"HyperTrack\.(isTracking\s*=\s*true|setIsTracking\s*\(\s*true|IsTracking\s*=\s*true)", text):
            report.warn("code", "local isTracking=true persists after orders complete; prefer backend orders", path)
        for match in LOCATION_LITERAL_RE.finditer(text):
            if abs(float(match.group(2))) > 90:
                report.fail("code", f"{match.group(0)}: first value isn't a latitude; SDK Location takes latitude, then longitude", path)
        if ext in (".kt", ".cs") and POSITIONAL_LOCATION_RE.search(text):
            report.warn("code", "positional HyperTrack.Location(...): pass latitude/longitude by name", path)
    if found_set:
        report.ok("code", "worker handle is set")
    else:
        report.fail("code", "worker handle is never set (set it on login and launch)")
    if found_set and not found_clear:
        report.warn("code", 'worker handle is never cleared: set it to "" on logout')
    if not found_errors:
        report.warn("code", "SDK errors are never read: subscribe to errors on the work screen")


def latest(platform):
    try:
        if platform == "maui":  # GitHub releases lag behind NuGet
            with urllib.request.urlopen("https://api.nuget.org/v3-flatcontainer/hypertrack.sdk.maui/index.json", timeout=10) as response:
                return json.load(response)["versions"][-1]
        url = f"https://api.github.com/repos/hypertrack/{LATEST_REPO[platform]}/releases/latest"
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"}), timeout=10) as response:
            return json.load(response).get("tag_name")
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Static audit of a mobile app's HyperTrack setup.")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--check-latest", action="store_true", help="compare detected SDK versions with GitHub releases")
    args = parser.parse_args()
    root = os.path.abspath(args.root)

    report, detected = audit(root)
    print(f"HyperTrack mobile audit: {root}")
    if not detected:
        print("No HyperTrack SDK dependency found (iOS pod/SPM, Gradle, npm, pub, or NuGet).")
        return 1
    print("Detected: " + ", ".join(f"{k} {v}" for k, v in detected.items()))
    if args.check_latest:
        for platform, version in detected.items():
            tag = latest(platform)
            if tag and version not in (tag, "?", "SPM"):
                print(f"  {platform}: {version} -> latest {tag}")
    order = {"FAIL": 0, "WARN": 1, "PASS": 2}
    for level, area, message in sorted(report.lines, key=lambda line: (order[line[0]], line[1])):
        print(f"{level:4}  {area:12} {message}")
    fails = sum(1 for line in report.lines if line[0] == "FAIL")
    warns = sum(1 for line in report.lines if line[0] == "WARN")
    print(f"\n{fails} FAIL, {warns} WARN")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
