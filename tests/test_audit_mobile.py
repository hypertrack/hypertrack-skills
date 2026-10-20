"""audit_mobile.py against small fixture projects."""

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

AUDIT = Path(__file__).resolve().parent.parent / "skills/hypertrack-integration/scripts/audit_mobile.py"

INFO_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>App</string>
<key>HyperTrackPublishableKey</key><string>pk_live_abc123</string>
<key>NSLocationWhenInUseUsageDescription</key><string>Shift arrival times.</string>
<key>NSLocationAlwaysAndWhenInUseUsageDescription</key><string>Shift arrival times, also in the background.</string>
<key>NSMotionUsageDescription</key><string>Activity detection.</string>
<key>UIBackgroundModes</key><array>{modes}</array>
</dict></plist>
"""

ENTITLEMENTS = """<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0"><dict><key>aps-environment</key><string>development</string></dict></plist>
"""

MANIFEST = """<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">
    <application>
        <meta-data
            android:name="HyperTrackPublishableKey"
            tools:replace="android:value"
            android:value="pk_live_abc123" />
    </application>
</manifest>
"""

GRADLE = """dependencies {
    implementation("com.hypertrack:sdk-android:7.14.0")
    implementation("com.hypertrack:location-services-google:7.14.0")
    implementation("com.hypertrack:push-service-firebase:7.14.0")
}
"""

SETTINGS_GRADLE = 'dependencyResolutionManagement { repositories { maven { url = uri("https://s3-us-west-2.amazonaws.com/m2.hypertrack.com/") } } }\n'

KOTLIN_OK = """import com.hypertrack.sdk.android.HyperTrack
fun login(id: String) { HyperTrack.workerHandle = id }
fun logout() { HyperTrack.workerHandle = "" }
fun errors() = HyperTrack.subscribeToErrors { }
fun expected() = HyperTrack.Location(latitude = 37.79, longitude = -122.39)
"""


def write(root, files):
    for relative, content in files.items():
        path = Path(root, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content))


def android_project(**overrides):
    files = {
        "settings.gradle.kts": SETTINGS_GRADLE,
        "app/build.gradle.kts": GRADLE,
        "app/google-services.json": "{}",
        "app/src/main/AndroidManifest.xml": MANIFEST,
        "app/src/main/java/App.kt": KOTLIN_OK,
    }
    files.update(overrides)
    return files


class AuditTest(unittest.TestCase):
    def audit(self, files):
        with tempfile.TemporaryDirectory() as root:
            write(root, files)
            result = subprocess.run([sys.executable, str(AUDIT), root], capture_output=True, text=True)
        lines = [line for line in result.stdout.splitlines() if line[:4] in ("FAIL", "WARN", "PASS")]
        return result.returncode, lines

    def assertLine(self, lines, level, text):
        self.assertTrue(any(line.startswith(level) and text in line for line in lines), "\n".join(lines))

    def assertNoLine(self, lines, level, text):
        self.assertFalse(any(line.startswith(level) and text in line for line in lines), "\n".join(lines))

    def test_complete_android_project_passes(self):
        code, lines = self.audit(android_project())
        self.assertEqual(code, 0, "\n".join(lines))
        self.assertLine(lines, "PASS", "HyperTrackPublishableKey meta-data set")
        self.assertLine(lines, "PASS", "artifacts aligned at 7.14.0")

    def test_manifest_key_found_with_attribute_between_name_and_value(self):
        _, lines = self.audit(android_project())
        self.assertNoLine(lines, "FAIL", "HyperTrackPublishableKey")

    def test_missing_manifest_key_fails(self):
        manifest = '<manifest xmlns:android="http://schemas.android.com/apk/res/android"><application /></manifest>'
        code, lines = self.audit(android_project(**{"app/src/main/AndroidManifest.xml": manifest}))
        self.assertEqual(code, 1)
        self.assertLine(lines, "FAIL", "HyperTrackPublishableKey <meta-data> missing")

    def test_mismatched_plugin_versions_fail(self):
        gradle = GRADLE.replace("push-service-firebase:7.14.0", "push-service-firebase:7.13.0")
        _, lines = self.audit(android_project(**{"app/build.gradle.kts": gradle}))
        self.assertLine(lines, "FAIL", "different versions")

    def test_missing_push_plugin_and_google_services_fail(self):
        files = android_project(**{"app/build.gradle.kts": GRADLE.replace("push-service-firebase", "x-unused")})
        files.pop("app/google-services.json")
        _, lines = self.audit(files)
        self.assertLine(lines, "FAIL", "push-service-firebase")
        self.assertLine(lines, "FAIL", "google-services.json not found")

    def test_swapped_location_literal_fails(self):
        code = KOTLIN_OK + "fun swapped() = HyperTrack.Location(-122.39, 37.79)\n"
        _, lines = self.audit(android_project(**{"app/src/main/java/App.kt": code}))
        self.assertLine(lines, "FAIL", "first value isn't a latitude")
        self.assertLine(lines, "WARN", "positional HyperTrack.Location")

    def test_worker_handle_never_set_fails_and_never_cleared_warns(self):
        _, never_set = self.audit(android_project(**{"app/src/main/java/App.kt": "import com.hypertrack.sdk.android.HyperTrack\n"}))
        self.assertLine(never_set, "FAIL", "worker handle is never set")
        code = KOTLIN_OK.replace('HyperTrack.workerHandle = ""', "Unit")
        _, never_cleared = self.audit(android_project(**{"app/src/main/java/App.kt": code}))
        self.assertLine(never_cleared, "WARN", "never cleared")

    def test_ios_missing_background_mode_and_push_entitlement_fail(self):
        files = {
            "Podfile.lock": "PODS:\n  - HyperTrack (5.14.0)\n",
            "App/Info.plist": INFO_PLIST.format(modes="<string>location</string>"),
            "App/App.swift": 'import HyperTrack\nfunc login() { HyperTrack.workerHandle = "u" }\n',
        }
        code, lines = self.audit(files)
        self.assertEqual(code, 1)
        self.assertLine(lines, "FAIL", "UIBackgroundModes missing 'remote-notification'")
        self.assertLine(lines, "FAIL", "aps-environment")

    def test_complete_ios_project_passes(self):
        files = {
            "Podfile.lock": "PODS:\n  - HyperTrack (5.14.0)\n",
            "App/Info.plist": INFO_PLIST.format(modes="<string>location</string><string>remote-notification</string>"),
            "App/App.entitlements": ENTITLEMENTS,
            "App/App.swift": 'import HyperTrack\nfunc a() { HyperTrack.workerHandle = "u"; HyperTrack.workerHandle = ""; _ = HyperTrack.errors }\n',
        }
        code, lines = self.audit(files)
        self.assertEqual(code, 0, "\n".join(lines))

    def test_known_api_mistakes_fail(self):
        files = android_project(**{
            "lib/main.dart": "import 'package:hypertrack_plugin/hypertrack.dart';\nvoid f() { HyperTrack.workerHandle = 'u'; }\n",
            "pubspec.yaml": "dependencies:\n  hypertrack_plugin: 3.2.0\n",
            "App/Errors.swift": "import HyperTrack\nfunc f(e: HyperTrack.Error) { if case .location(.permissions(.denied)) = e {} }\n",
        })
        _, lines = self.audit(files)
        self.assertLine(lines, "FAIL", "Flutter: HyperTrack.workerHandle has no setter")
        self.assertLine(lines, "FAIL", "Swift: error pattern")

    def test_react_native_plugin_versions_must_match(self):
        package = """{"dependencies": {
            "hypertrack-sdk-react-native": "^14.2.0",
            "hypertrack-sdk-react-native-plugin-android-location-services-google": "^14.2.0",
            "hypertrack-sdk-react-native-plugin-android-push-service-firebase": "^14.1.0"}}"""
        _, lines = self.audit({"package.json": package, "App.tsx": "HyperTrack.setWorkerHandle('u')\n"})
        self.assertLine(lines, "FAIL", "HyperTrack package versions differ")

    def test_secret_key_reference_in_app_warns(self):
        code = KOTLIN_OK + 'val secret = BuildConfig.HYPERTRACK_SECRET_KEY\n'
        _, lines = self.audit(android_project(**{"app/src/main/java/App.kt": code}))
        self.assertLine(lines, "WARN", "secrets must stay server-side")

    def test_maui_workaround_condition_must_match_target_framework(self):
        csproj = """<Project Sdk="Microsoft.NET.Sdk">
          <PropertyGroup><TargetFrameworks>net10.0-android;net10.0-ios</TargetFrameworks></PropertyGroup>
          <ItemGroup>
            <PackageReference Include="HyperTrack.SDK.MAUI" Version="1.0.4" />
            <AndroidMavenLibrary Include="com.hypertrack:sdk-android-model" Version="7.11.4" Bind="false" Condition="'$(TargetFramework)' == '{framework}'" />
            <GoogleServicesJson Include="google-services.json" />
          </ItemGroup>
        </Project>"""
        code = "namespace App;\nusing HyperTrack;\nclass A { void B() { HyperTrack.WorkerHandle = \"u\"; } }\n"
        _, mismatched = self.audit({"App.csproj": csproj.replace("{framework}", "net9.0-android"), "A.cs": code})
        self.assertLine(mismatched, "FAIL", "never applies")
        _, matched = self.audit({"App.csproj": csproj.replace("{framework}", "net10.0-android"), "A.cs": code})
        self.assertNoLine(matched, "FAIL", "never applies")

    def test_no_hypertrack_dependency_exits_nonzero(self):
        code, _ = self.audit({"README.md": "nothing here"})
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
