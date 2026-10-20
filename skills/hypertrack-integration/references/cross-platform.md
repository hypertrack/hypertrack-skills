# Cross-platform SDKs

React Native, Expo, Flutter, Ionic Capacitor, and .NET MAUI wrap the native SDKs. The native rules still apply: publishable key in `Info.plist`/`AndroidManifest.xml`, iOS Background Modes and Push capability, purpose strings, APNs and FCM keys on the dashboard, and two-step permissions. Read `mobile.md` first, then the native sections linked below.

None of these wrappers expose on-device orders (`orders.track`); that API is native-only.

| Platform        | Package (latest version: GitHub `releases/latest`; MAUI: NuGet) | Repo                             |
| --------------- | --------------------------------------------------------------- | -------------------------------- |
| React Native    | `hypertrack-sdk-react-native` + Android plugin packages         | `hypertrack/sdk-react-native`    |
| Expo            | `hypertrack-sdk-expo` + the React Native packages               | `hypertrack/sdk-expo`            |
| Flutter         | `hypertrack_plugin` (pub.dev)                                   | `hypertrack/sdk-flutter`         |
| Ionic Capacitor | `hypertrack-sdk-ionic-capacitor`                                | `hypertrack/sdk-ionic-capacitor` |
| .NET MAUI       | `HyperTrack.SDK.MAUI` (NuGet)                                   | `hypertrack/sdk-maui`            |

TypeScript, Dart, and C# blocks here compile against the published SDK packages.

## React Native

```bash
npm install hypertrack-sdk-react-native \
  hypertrack-sdk-react-native-plugin-android-location-services-google \
  hypertrack-sdk-react-native-plugin-android-push-service-firebase \
  hypertrack-sdk-react-native-plugin-android-activity-service-google
```

- All plugin packages use **the same version** as `hypertrack-sdk-react-native`. The activity plugin is optional. If the app pins `play-services-location` ≤ 19.0.1, use `hypertrack-sdk-react-native-plugin-android-location-services-google-19-0-1` instead.
- Android: add the HyperTrack Maven repo (`android.md` § Install), the publishable key `<meta-data>`, Firebase (`google-services.json` + plugin), and ProGuard rules if minifying.
- iOS: `cd ios && pod install`, then everything in `ios.md` § Project configuration and § Silent push.

```ts
import HyperTrack, { HyperTrackError, type OrderStatus } from 'hypertrack-sdk-react-native';

export function onLogin(userId: string, displayName: string) {
  HyperTrack.setWorkerHandle(userId);
  HyperTrack.setName(displayName);
  HyperTrack.setMetadata({ team: 'north' });
}

export function onLogout() {
  HyperTrack.setWorkerHandle('');
}

function handleErrors(errors: HyperTrackError[]) {
  for (const error of errors) {
    switch (error) {
      case HyperTrackError.permissionsLocationDenied:
      case HyperTrackError.permissionsLocationInsufficientForBackground:
      case HyperTrackError.permissionsLocationReducedAccuracy:
        // Explain and link to Settings.
        break;
      case HyperTrackError.locationServicesDisabled:
        // Ask the worker to turn on location.
        break;
      default:
        break;
    }
  }
}

export function observeErrors() {
  HyperTrack.getErrors().then(handleErrors);
  return HyperTrack.subscribeToErrors(handleErrors); // call .remove() when done
}

export async function clockIn(orderHandle: string) {
  const clockInStatus: OrderStatus = { type: 'orderStatusClockIn' };
  const result = await HyperTrack.addGeotag(orderHandle, clockInStatus, { source: 'worker_app' });
  if (result.type === 'failure') {
    console.warn('Clock-in recorded without a fresh location', result.value);
  }
}

export function observeClockInGate(orderHandle: string, onChange: (canClockIn: boolean) => void) {
  return HyperTrack.subscribeToOrders(async (orders) => {
    const order = orders.get(orderHandle);
    const inside = order ? await order.isInsideGeofence() : undefined;
    onChange(inside?.type === 'success' && inside.value);
  }); // call .remove() when the screen goes away
}

export function setAvailable(available: boolean) {
  HyperTrack.setIsAvailable(available);
}
```

Order statuses: `{ type: 'orderStatusClockIn' }`, `{ type: 'orderStatusClockOut' }`, `{ type: 'orderStatusCustom', value: 'break_start' }`. Request location permissions with your permissions library (for example `react-native-permissions`), using the two-step order from `mobile.md`.

## Expo

```bash
npx expo install hypertrack-sdk-expo hypertrack-sdk-react-native \
  hypertrack-sdk-react-native-plugin-android-location-services-google \
  hypertrack-sdk-react-native-plugin-android-push-service-firebase \
  hypertrack-sdk-react-native-plugin-android-activity-service-google
```

`app.json` / `app.config.*`:

```json
{
  "expo": {
    "plugins": [
      [
        "hypertrack-sdk-expo",
        {
          "publishableKey": "YOUR_PUBLISHABLE_KEY",
          "locationPermission": "Your location is used during shifts, even when the app is closed, to record arrival times.",
          "motionPermission": "Motion data improves activity detection in your shift timeline.",
          "foregroundNotificationTitle": "Shift tracking active",
          "foregroundNotificationText": "Your location is tracked during your shift."
        }
      ]
    ]
  }
}
```

- The plugin sets the publishable key, the iOS purpose strings, the iOS Background Modes (`location`, `remote-notification`), the Android Maven repo, and the foreground-notification copy. Other params: `allowMockLocation`, and `proxyDevicePushTokenCall` (set it to `true` if iOS devices end up without a push token).
- Run `npx expo prebuild` after changing plugin params. Expo Go doesn't work; use a development build.
- Push still needs the native pieces: the iOS Push Notifications capability (`aps-environment`), `android.googleServicesFile` pointing at `google-services.json`, and the APNs `.p8` plus FCM JSON uploaded to the **HyperTrack** dashboard. Expo's own push credentials don't cover this.
- EAS or Fastlane release automation can't fill the Google Play permission forms. Do one manual release first (`production.md`).
- The API is the React Native one (above).

## Flutter

```yaml
dependencies:
  hypertrack_plugin: <version>
```

- The plugin pulls in all the Android plugin artifacts and declares HyperTrack's Maven repo. If the app enforces settings-only repositories (`RepositoriesMode.FAIL_ON_PROJECT_REPOS`), add the repo to `settings.gradle` yourself.
- Android: publishable key `<meta-data>`, Firebase `google-services.json`. iOS: `ios.md` § Project configuration.
- **Flutter + Firebase on iOS:** swizzling conflicts. Set `HyperTrackSwizzlingEnabled` to `NO` and forward the four `AppDelegate` calls in your `FlutterAppDelegate` subclass, calling `super` too (`ios.md` § Silent push).

```dart
import 'package:hypertrack_plugin/hypertrack.dart';
import 'package:hypertrack_plugin/data_types/hypertrack_error.dart';
import 'package:hypertrack_plugin/data_types/json.dart';
import 'package:hypertrack_plugin/data_types/location_error.dart';
import 'package:hypertrack_plugin/data_types/order_status.dart';
import 'package:hypertrack_plugin/data_types/result.dart';

void onLogin(String userId, String displayName) {
  HyperTrack.setWorkerHandle(userId); // workerHandle has no setter
  HyperTrack.setName(displayName);
  HyperTrack.setMetadata(JSONObject({"team": JSONString("north")}));
}

void onLogout() => HyperTrack.setWorkerHandle("");

final errorsSubscription = HyperTrack.errorsSubscription.listen((errors) {
  if (errors.contains(HyperTrackError.permissionsLocationDenied)) {
    // Explain and link to Settings.
  }
}); // cancel() when done

Future<void> clockIn(String orderHandle) async {
  final result = await HyperTrack.addGeotag(
    orderHandle,
    OrderStatus.clockIn(),
    JSONObject({"source": JSONString("worker_app")}),
  );
  if (result is Failure) {
    // Clock-in recorded without a fresh location.
  }
}

Future<bool> canClockIn(String orderHandle) async {
  final order = (await HyperTrack.orders)[orderHandle];
  if (order == null) return false;
  final inside = await order.isInsideGeofence;
  return inside is Success<bool, LocationError> && inside.value;
}

void setAvailable(bool available) => HyperTrack.setIsAvailable(available);
```

Also available: `HyperTrack.errors` (a `Future`), `ordersSubscription`, `OrderStatus.clockOut()`, `OrderStatus.custom("break_start")`, and `addGeotagWithExpectedLocation`. Reference: `https://hypertrack.github.io/sdk-flutter/`.

## Ionic Capacitor

```bash
npm install hypertrack-sdk-ionic-capacitor
npx cap sync
```

- The Android plugin depends on every HyperTrack Android artifact and declares the Maven repo. Add the publishable key `<meta-data>` and Firebase. iOS: `npx cap sync` installs the pod; then follow `ios.md` § Project configuration and § Silent push.
- The API matches React Native's, but you import from `hypertrack-sdk-ionic-capacitor`, and `subscribeTo*` returns a `Subscription` whose `remove()` returns a promise.

```ts
import HyperTrack, { HyperTrackError } from 'hypertrack-sdk-ionic-capacitor';

export function onLogin(userId: string) {
  HyperTrack.setWorkerHandle(userId);
}

export function onLogout() {
  HyperTrack.setWorkerHandle('');
}

export function observeErrors() {
  return HyperTrack.subscribeToErrors((errors) => {
    if (errors.includes(HyperTrackError.permissionsLocationDenied)) {
      // Explain and link to Settings.
    }
  });
}

export async function clockIn(orderHandle: string) {
  await HyperTrack.addGeotag(orderHandle, { type: 'orderStatusClockIn' }, { source: 'worker_app' });
}
```

## .NET MAUI

```xml
<ItemGroup>
    <PackageReference Include="HyperTrack.SDK.MAUI" Version="VERSION" />
    <!-- Workaround for a MAUI packaging bug with .jar-providing Android libraries -->
    <AndroidMavenLibrary Include="com.hypertrack:sdk-android-model" Version="7.11.4" Repository="https://s3-us-west-2.amazonaws.com/m2.hypertrack.com/" Bind="false" Condition="'$(TargetFramework)' == 'net10.0-android'" />
    <AndroidMavenLibrary Include="org.jetbrains.kotlinx:kotlinx-serialization-json-jvm" Version="1.3.3" Bind="false" Condition="'$(TargetFramework)' == 'net10.0-android'" />
    <AndroidIgnoredJavaDependency Include="org.jetbrains.kotlin:kotlin-stdlib:1.6.21" />
    <AndroidIgnoredJavaDependency Include="org.jetbrains.kotlin:kotlin-stdlib-jdk8:1.6.21" />
    <AndroidIgnoredJavaDependency Include="org.jetbrains.kotlin:kotlin-stdlib-common:1.6.21" />
    <AndroidIgnoredJavaDependency Include="org.jetbrains.kotlinx:kotlinx-serialization-core-jvm:1.3.3" />
</ItemGroup>
```

- Get the latest version from NuGet (`https://api.nuget.org/v3-flatcontainer/hypertrack.sdk.maui/index.json`), not GitHub releases. `HyperTrack.SDK.MAUI` 1.0.4 and later target .NET 10 (`net10.0-android` / `net10.0-ios`); 1.0.3 and earlier target .NET 9. The workaround block above is the one from the package README. Copy it from the README of the version you install, with the `Condition` matching your target framework.
- Publishable key: `Platforms/iOS/Info.plist` and `Platforms/Android/AndroidManifest.xml`. iOS capabilities, purpose strings, and APNs as in `ios.md`.
- FCM on Android: the quickstart uses `Plugin.Firebase.CloudMessaging` plus `<GoogleServicesJson Include="google-services.json" />`.
- `HyperTrack` is both the namespace and the class. Put `using HyperTrack;` **after** the `namespace` line; above it, `HyperTrack.WorkerHandle` resolves to the namespace and fails with CS0234.

```csharp
namespace YourApp;

using HyperTrack;

public class HyperTrackSetup
{
    private HyperTrack.ICancellable? errorsSubscription;

    public void OnLogin(string userId, string displayName)
    {
        HyperTrack.WorkerHandle = userId;
        HyperTrack.Name = displayName;
        HyperTrack.Metadata = HyperTrack.Json.FromDictionary(new Dictionary<string, object> { { "team", "north" } });
    }

    public void OnLogout() => HyperTrack.WorkerHandle = "";

    public void ObserveErrors()
    {
        errorsSubscription = HyperTrack.SubscribeToErrors(errors =>
        {
            foreach (var error in errors)
            {
                switch (error)
                {
                    case HyperTrack.Error.Permissions.Location.Denied:
                    case HyperTrack.Error.Permissions.Location.InsufficientForBackground:
                        // Explain and link to Settings.
                        break;
                    case HyperTrack.Error.Location.ServicesDisabled:
                        // Ask the worker to turn on location.
                        break;
                }
            }
        });
    }

    public void StopObservingErrors() => errorsSubscription?.Cancel();

    public bool ClockIn(string orderHandle)
    {
        var metadata = HyperTrack.Json.FromDictionary(new Dictionary<string, object> { { "source", "worker_app" } });
        return HyperTrack.AddGeotag(orderHandle, new HyperTrack.OrderStatus.ClockIn(), metadata).IsSuccess;
    }

    public bool CanClockIn(string orderHandle) =>
        HyperTrack.Orders.TryGetValue(orderHandle, out var order)
        && order.IsInsideGeofence.IsSuccess
        && order.IsInsideGeofence.Success;

    public void SetAvailable(bool available) => HyperTrack.IsAvailable = available;
}
```

Reference: `https://hypertrack.github.io/sdk-maui/class_hyper_track_1_1_hyper_track.html` and `https://github.com/hypertrack/quickstart-maui`.
