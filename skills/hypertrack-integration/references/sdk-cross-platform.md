# Cross-Platform SDK Integration

This reference covers React Native, Expo, Flutter, Ionic Capacitor, and .NET MAUI. All wrap the native iOS and Android SDKs.

**Important:** Each cross-platform SDK still requires native platform setup. You must complete the platform-specific steps from `sdk-ios.md` and `sdk-android.md` for:

- Silent push notifications (APNs + FCM)
- Publishable key configuration
- Background modes (iOS)
- Location permissions

This reference covers the cross-platform layer on top.

---

## React Native

### Install

```bash
npm install hypertrack-sdk-react-native \
  hypertrack-sdk-react-native-plugin-android-location-services-google \
  hypertrack-sdk-react-native-plugin-android-activity-service-google \
  hypertrack-sdk-react-native-plugin-android-push-service-firebase
```

> All plugin versions must match the main SDK version.

### Native setup (required)

**Android:**

- Add HyperTrack Maven repository in Gradle (see `sdk-android.md`)
- Configure ProGuard if minification is enabled
- Set `HyperTrackPublishableKey` in AndroidManifest.xml
- Set up FCM and upload service account key

**iOS:**

- Run `cd ios && pod install`
- Enable Background Modes (Location updates + Remote notifications)
- Add purpose strings to Info.plist
- Set `HyperTrackPublishableKey` in Info.plist
- Upload APNs key to dashboard

### Worker handle

```javascript
import HyperTrack from 'hypertrack-sdk-react-native';

// On login
HyperTrack.setWorkerHandle("your_user_id");

// On logout
HyperTrack.setWorkerHandle("");
```

### Name and metadata

```javascript
HyperTrack.setName("Jane Smith");
HyperTrack.setMetadata({
    department: "nursing",
    skills: ["ICU", "ER"]
});
```

### Error handling

```javascript
// Query
const errors = await HyperTrack.getErrors();
errors.forEach(error => { /* handle */ });

// Subscribe
const subscription = HyperTrack.subscribeToErrors(errors => {
    errors.forEach(error => { /* handle */ });
});

// Unsubscribe
subscription.remove();
```

### Geotags

```javascript
HyperTrack.addGeotag(
    "shift-123",
    { type: "orderStatusClockIn" },
    { facility: "Building A" }
);
```

### Availability

```javascript
HyperTrack.setIsAvailable(true);
HyperTrack.setIsAvailable(false);
```

### References

- [SDK Reference](https://hypertrack.github.io/sdk-react-native/)
- [Quickstart](https://github.com/hypertrack/quickstart-react-native)
- [Install guide](https://hypertrack.com/docs/install-sdk-react-native)

---

## Expo

### Install

```bash
npx expo install hypertrack-sdk-expo \
  hypertrack-sdk-react-native \
  hypertrack-sdk-react-native-plugin-android-location-services-google \
  hypertrack-sdk-react-native-plugin-android-activity-service-google \
  hypertrack-sdk-react-native-plugin-android-push-service-firebase
```

### Configure Expo plugin

In `app.json` or `app.config.js`:

```json
{
  "expo": {
    "plugins": [
      [
        "hypertrack-sdk-expo",
        {
          "publishableKey": "your-publishable-key",
          "locationPermission": "YourApp uses location to track your shifts and provide accurate arrival times.",
          "motionPermission": "YourApp uses motion data to improve activity detection during shifts."
        }
      ]
    ]
  }
}
```

> Rebuild the native app after changing plugin config (`npx expo prebuild`).

The Expo plugin handles iOS purpose strings via `locationPermission` and `motionPermission` parameters. You still need to:

- Set up push notifications for both platforms
- Upload APNs credentials and FCM service account key to HyperTrack dashboard

### Push notifications for Expo

- **iOS:** Add push notification credentials via `eas credentials` or Expo dashboard
- **Android:** Set up FCM using Expo's [FCM guide](https://docs.expo.dev/push-notifications/fcm-credentials/)

For bare workflow, follow the React Native manual setup above.

### API usage

Same as React Native — use `hypertrack-sdk-react-native` imports:

```javascript
import HyperTrack from 'hypertrack-sdk-react-native';

HyperTrack.setWorkerHandle("your_user_id");
```

### References

- [Quickstart](https://github.com/hypertrack/quickstart-expo)
- [Install guide](https://hypertrack.com/docs/install-sdk-expo)

---

## Flutter

### Install

In `pubspec.yaml`:

```yaml
dependencies:
  hypertrack_plugin: <version>
```

### Native setup

**Android:** Same as `sdk-android.md` (Maven repo, Gradle deps, FCM, publishable key).

**iOS:**

- Enable Background Modes
- Add purpose strings
- Set publishable key in Info.plist

### iOS AppDelegate setup (required)

Flutter's Firebase plugin conflicts with HyperTrack's swizzling. Add to `Info.plist`:

```xml
<key>HyperTrackSwizzlingEnabled</key>
<false/>
```

Then override AppDelegate methods:

```swift
import HyperTrack

@UIApplicationMain
@objc class AppDelegate: FlutterAppDelegate {
    override func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        HyperTrack.didFinishLaunchingWithOptions(launchOptions)
        GeneratedPluginRegistrant.register(with: self)
        return super.application(application, didFinishLaunchingWithOptions: launchOptions)
    }

    override func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        HyperTrack.didRegisterForRemoteNotificationsWithDeviceToken(deviceToken)
        super.application(application, didRegisterForRemoteNotificationsWithDeviceToken: deviceToken)
    }

    override func application(
        _ application: UIApplication,
        didReceiveRemoteNotification userInfo: [AnyHashable: Any],
        fetchCompletionHandler completionHandler: @escaping (UIBackgroundFetchResult) -> Void
    ) {
        HyperTrack.didReceiveRemoteNotification(userInfo, fetchCompletionHandler: completionHandler)
        super.application(application, didReceiveRemoteNotification: userInfo, fetchCompletionHandler: completionHandler)
    }

    override func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        HyperTrack.didFailToRegisterForRemoteNotificationsWithError(error)
        super.application(application, didFailToRegisterForRemoteNotificationsWithError: error)
    }
}
```

### Worker handle

```dart
HyperTrack.workerHandle = "your_user_id";  // login
HyperTrack.workerHandle = "";              // logout
```

### Name and metadata

```dart
HyperTrack.setName("Jane Smith");
HyperTrack.setMetadata(JSONObject({
    "department": JSONString("nursing"),
}));
```

### Error handling

```dart
HyperTrack.errorsSubscription.listen((errors) {
    errors.forEach((error) {
        switch (error) {
            // handle each error type
        }
    });
});
```

### References

- [SDK Reference](https://hypertrack.github.io/sdk-flutter/)
- [Quickstart](https://github.com/hypertrack/quickstart-flutter)
- [Install guide](https://hypertrack.com/docs/install-sdk-flutter)

---

## Ionic Capacitor

### Install

```bash
npm install hypertrack-sdk-ionic-capacitor
```

**iOS:** Run `cd ios && pod install`. Enable Background Modes, add purpose strings.

**Android:** Add Maven repo, set publishable key in manifest.

### API

```typescript
import HyperTrack from 'hypertrack-sdk-ionic-capacitor';

HyperTrack.setWorkerHandle("your_user_id");
HyperTrack.setName("Jane Smith");
HyperTrack.setMetadata({ department: "nursing" });

// Errors
const errors = await HyperTrack.getErrors();
const sub = HyperTrack.subscribeToErrors(errors => { /* handle */ });
sub.remove();
```

### References

- [SDK Reference](https://hypertrack.github.io/sdk-ionic-capacitor/)
- [Quickstart](https://github.com/hypertrack/quickstart-ionic-capacitor)
- [Install guide](https://hypertrack.com/docs/install-sdk-ionic-capacitor)

---

## .NET MAUI

### Install

In your `.csproj`:

```xml
<ItemGroup>
    <PackageReference Include="HyperTrack.SDK.MAUI" Version="<version>" />

    <!-- Android workarounds for MAUI packaging bug -->
    <AndroidMavenLibrary Include="com.hypertrack:sdk-android-model" Version="7.11.4"
        Repository="https://s3-us-west-2.amazonaws.com/m2.hypertrack.com/"
        Bind="false" Condition="'$(TargetFramework)' == 'net9.0-android'" />
    <AndroidMavenLibrary Include="org.jetbrains.kotlinx:kotlinx-serialization-json-jvm"
        Version="1.3.3" Bind="false"
        Condition="'$(TargetFramework)' == 'net9.0-android'" />
    <AndroidIgnoredJavaDependency Include="org.jetbrains.kotlin:kotlin-stdlib:1.6.21" />
    <AndroidIgnoredJavaDependency Include="org.jetbrains.kotlin:kotlin-stdlib-jdk8:1.6.21" />
    <AndroidIgnoredJavaDependency Include="org.jetbrains.kotlin:kotlin-stdlib-common:1.6.21" />
    <AndroidIgnoredJavaDependency Include="org.jetbrains.kotlinx:kotlinx-serialization-core-jvm:1.3.3" />
</ItemGroup>
```

Requires .NET MAUI 9.0+.

### Native setup

Same native-level setup required:

- **Android:** FCM service account key, publishable key in manifest
- **iOS:** APNs key, Background Modes, purpose strings, publishable key in Info.plist

### API

```csharp
// Login
HyperTrack.SetWorkerHandle("your_user_id");

// Logout
HyperTrack.SetWorkerHandle("");

// Name + metadata
HyperTrack.Name = "Jane Smith";
HyperTrack.Metadata = HyperTrack.Json.FromDictionary(new Dictionary<string, object> {
    { "department", "nursing" },
    { "skills", new[] { "ICU" } }
})!;

// Error handling
HyperTrack.SubscribeToErrors(errors => {
    foreach (var error in errors) {
        switch (error) {
            case HyperTrackError.LocationPermissionsDenied:
                // handle
                break;
        }
    }
});

// Geotags
var result = HyperTrack.AddGeotag(
    "shift-123",
    new HyperTrack.OrderStatus.ClockIn(),
    metadata
);
```

### References

- [SDK Reference](https://hypertrack.github.io/sdk-maui/)
- [Quickstart](https://github.com/hypertrack/quickstart-maui)
- [Install guide](https://hypertrack.com/docs/install-sdk-maui)
