# VIDHIK Android Packaging — Readiness Checklist

This is the verification companion to `frontend-build/README.md` and the PowerShell scripts. It does not change the app. It only helps you avoid the most common first-run failures.

## 1. Frontend source of truth

Confirm the existing web app you want to package is at:

- `backend/app/static/index.html`
- `backend/app/static/app.js`
- `backend/app/static/i18n.js`
- `backend/app/static/styles.css`

If your real deployed frontend lives elsewhere, change the source before packaging.

## 2. Node toolchain

Confirm these resolve on your Windows machine:

- `node --version`
- `npm --version`
- `npx --version`

The packaging scripts use `npx cap ...`, so `npx` must be available.

## 3. Android SDK environment

The Android build will need:

- Java 17+ JDK
- Android SDK
- `ANDROID_HOME` or `ANDROID_SDK_ROOT` pointing at the SDK root

Typical failure mode: the Capacitor sync works, but the Gradle build fails because the SDK is not visible.

Quick checks:

- `echo $env:ANDROID_HOME`
- `echo $env:ANDROID_SDK_ROOT`
- `java -version`

If either SDK variable is empty, set it before building. If you use Android Studio, the SDK path is usually under your user profile AppData.

## 4. Do not mix up the PowerShell commands

A common first-run mistake is pasting several lines as one command. The commands below must be run one at a time, or pasted as separate lines.

Also note:
- The one-time setup uses `npx cap init VIDHIK com.vidhik.app --web-dir=../backend/app/static`
- The repeatable build uses `npx cap build android --production`

If you see errors like “unknown option” or “could not find web assets directory,” stop and check:
- whether `frontend-build/capacitor.config.json` exists,
- whether `webDir` points to a folder that contains `index.html`,
- whether you installed `@capacitor/android` before running `npx cap add android`.

## 5. The exact commands

### Once — scaffold the Android wrapper

Run from the repository root:

```powershell
cd frontend-build
npm init -y
npm install @capacitor/core@latest @capacitor/cli@latest
npx cap init VIDHIK com.vidhik.app --web-dir=../backend/app/static
npm install @capacitor/android@latest
npx cap add android
npx cap sync
```

### Every build — rebuild the APK

```powershell
cd frontend-build
npx cap sync
npx cap build android --production
```

APK output is under `frontend-build/android/app/build/outputs/apk/`.

### Run on device/emulator

```powershell
cd frontend-build
npx cap run android
```

## 6. Clean rebuild

```powershell
cd frontend-build
npx cap clean
npx cap sync
npx cap build android --production
```

## 7. If the build fails, check these first

1. Does `frontend-build/capacitor.config.json` exist and is `webDir` correct?
2. Does `backend/app/static/index.html` still exist?
3. Is `@capacitor/android` installed in `frontend-build/node_modules`?
4. Is `frontend-build/android/` present?
5. Is the Android SDK visible to Gradle (`ANDROID_HOME` / `ANDROID_SDK_ROOT`)?
6. Is Java on the path and the right version for the Android tooling?

## 8. Important scope notes

- The packaging does not change how the app reaches its backend.
- The APK runs the existing web frontend in a WebView.
- If the app calls `/api/...` or your backend base URL, make sure the device/emulator can reach that backend before packaging, or configure the app’s backend URL before building.
- Packaging does not magically add native features. If you need camera, files, push, storage, or similar, add the relevant Capacitor plugins and sync.

## 9. What is already in this repo from the earlier packaging attempt

- `frontend-build/capacitor.config.json`
- `frontend-build/android/` (Android target added earlier)
- `frontend-build/init-android.ps1`
- `frontend-build/build-android.ps1`
- `frontend-build/README.md`

If those are already present, you may not need to run the “once” scaffolding again unless something was deleted.
