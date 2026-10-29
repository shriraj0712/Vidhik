import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Persists the authentication token in the platform keystore/Keychain.
///
/// Non-secret preferences (language, theme, backend URL) live in
/// SharedPreferences. Every plugin call is guarded so the app still boots on
/// platforms where a plugin is unavailable (for example widget tests).
class TokenStore {
  TokenStore();

  static const _tokenKey = 'vidhik_token';
  // flutter_secure_storage 11 encrypts with AES-GCM and an Android
  // Keystore-wrapped key by default, so no legacy flag is required.
  static const _secure = FlutterSecureStorage(aOptions: AndroidOptions());

  String? _cachedToken;
  String? get cachedToken => _cachedToken;

  Future<String?> readToken() async {
    if (_cachedToken != null) return _cachedToken;
    try {
      _cachedToken = await _secure.read(key: _tokenKey);
      if (_cachedToken != null && _cachedToken!.isEmpty) _cachedToken = null;
    } catch (_) {
      try {
        final prefs = await SharedPreferences.getInstance();
        _cachedToken = prefs.getString(_tokenKey);
      } catch (_) {
        _cachedToken = null;
      }
    }
    return _cachedToken;
  }

  Future<void> writeToken(String? token) async {
    _cachedToken = token;
    try {
      if (token == null) {
        await _secure.delete(key: _tokenKey);
      } else {
        await _secure.write(key: _tokenKey, value: token);
      }
      return;
    } catch (_) {
      // Fall back to preferences only when the secure store is unavailable.
    }
    try {
      final prefs = await SharedPreferences.getInstance();
      if (token == null) {
        await prefs.remove(_tokenKey);
      } else {
        await prefs.setString(_tokenKey, token);
      }
    } catch (_) {
      // Ignore: a missing token simply signs the user out.
    }
  }

  Future<void> clear() => writeToken(null);

  Future<String?> readPreference(String key) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getString(key);
    } catch (_) {
      return null;
    }
  }

  Future<void> writePreference(String key, String? value) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      if (value == null) {
        await prefs.remove(key);
      } else {
        await prefs.setString(key, value);
      }
    } catch (_) {
      // Ignore preference write failures.
    }
  }
}
