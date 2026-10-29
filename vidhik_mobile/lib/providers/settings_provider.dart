import 'package:flutter/material.dart';

import '../core/config/app_config.dart';
import '../core/network/api_client.dart';
import '../core/storage/token_store.dart';

/// User-controlled runtime settings. The backend URL is editable so a real
/// Android phone can point at a LAN or deployed backend without rebuilding.
class SettingsProvider extends ChangeNotifier {
  SettingsProvider({required this.client, required this.store}) {
    client.baseUrl = AppConfig.defaultBaseUrl;
  }

  final ApiClient client;
  final TokenStore store;

  String _baseUrl = AppConfig.defaultBaseUrl;
  String _language = 'en';
  ThemeMode _themeMode = ThemeMode.light;
  bool _loaded = false;

  String get baseUrl => _baseUrl;
  String get language => _language;
  ThemeMode get themeMode => _themeMode;
  bool get loaded => _loaded;

  static const languageNames = {
    'en': 'English',
    'hi': 'हिन्दी (Hindi)',
    'mr': 'मराठी (Marathi)',
  };

  String get languageLabel => languageNames[_language] ?? 'English';

  Future<void> load() async {
    final savedUrl = await store.readPreference('api_base_url');
    if (savedUrl != null && AppConfig.isValidBaseUrl(savedUrl)) {
      _baseUrl = AppConfig.normalizeBaseUrl(savedUrl);
    }
    final savedLanguage = await store.readPreference('language');
    if (savedLanguage != null && languageNames.containsKey(savedLanguage)) {
      _language = savedLanguage;
    }
    final savedTheme = await store.readPreference('theme_mode');
    if (savedTheme == 'dark') _themeMode = ThemeMode.dark;
    if (savedTheme == 'light') _themeMode = ThemeMode.light;
    client.baseUrl = _baseUrl;
    _loaded = true;
    notifyListeners();
  }

  Future<bool> setBaseUrl(String value) async {
    final trimmed = value.trim();
    if (!AppConfig.isValidBaseUrl(trimmed)) return false;
    _baseUrl = AppConfig.normalizeBaseUrl(trimmed);
    client.baseUrl = _baseUrl;
    await store.writePreference('api_base_url', _baseUrl);
    notifyListeners();
    return true;
  }

  Future<void> resetBaseUrl() async {
    _baseUrl = AppConfig.defaultBaseUrl;
    client.baseUrl = _baseUrl;
    await store.writePreference('api_base_url', null);
    notifyListeners();
  }

  Future<void> setLanguage(String value) async {
    if (!languageNames.containsKey(value)) return;
    _language = value;
    await store.writePreference('language', value);
    notifyListeners();
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    _themeMode = mode;
    await store.writePreference(
      'theme_mode',
      mode == ThemeMode.dark ? 'dark' : 'light',
    );
    notifyListeners();
  }
}
