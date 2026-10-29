import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';

/// Central application configuration.
///
/// The backend base URL is never hardcoded to a developer machine in the
/// shipped APK. It is resolved in this order:
///   1. The value the user saved in Settings (persisted on the device).
///   2. `--dart-define=API_BASE_URL=...` supplied at build time.
///   3. A sensible local default for the current platform.
class AppConfig {
  AppConfig._();

  static const String appName = 'VIDHIK AI';
  static const String tagline = 'Know your rights. Understand the law.';
  static const String version = '1.0.0';

  /// Build-time override: `flutter build apk --dart-define=API_BASE_URL=https://...`
  static const String compiledBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: '',
  );

  /// Android emulators reach the host machine through 10.0.2.2, while desktop
  /// and web builds can use loopback directly.
  static String get defaultBaseUrl {
    if (compiledBaseUrl.isNotEmpty) return _normalize(compiledBaseUrl);
    if (kIsWeb) return 'http://127.0.0.1:8000';
    if (Platform.isAndroid) return 'http://10.0.2.2:8000';
    return 'http://127.0.0.1:8000';
  }

  static String _normalize(String value) {
    var v = value.trim();
    while (v.endsWith('/')) {
      v = v.substring(0, v.length - 1);
    }
    return v;
  }

  static String normalizeBaseUrl(String value) => _normalize(value);

  static bool isValidBaseUrl(String value) {
    final uri = Uri.tryParse(_normalize(value));
    return uri != null &&
        (uri.scheme == 'http' || uri.scheme == 'https') &&
        uri.host.isNotEmpty;
  }
}
