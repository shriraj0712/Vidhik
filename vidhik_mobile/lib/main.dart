import 'package:flutter/foundation.dart' show kDebugMode;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'app.dart';
import 'core/network/api_client.dart';
import 'core/storage/token_store.dart';
import 'providers/auth_provider.dart';
import 'providers/chat_provider.dart';
import 'providers/settings_provider.dart';
import 'services/api_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final store = TokenStore();

  // Debug-only test hook: `flutter run --dart-define=DEBUG_AUTH_TOKEN=<jwt>`
  // seeds a real backend session so authenticated screens can be exercised on a
  // device when the CAPTCHA widget cannot run for the local hostname. Release
  // builds ignore this because kDebugMode is false and the default is empty.
  if (kDebugMode) {
    const seededToken = String.fromEnvironment('DEBUG_AUTH_TOKEN');
    if (seededToken.isNotEmpty) {
      await store.writeToken(seededToken);
    }
  }

  final client = ApiClient(tokenStore: store);
  final settings = SettingsProvider(client: client, store: store);
  await settings.load();

  final api = ApiService(client);
  final auth = AuthProvider(api: api, client: client, store: store);
  final chat = ChatProvider(api: api);

  // Kick off session restoration while the splash screen is visible.
  auth.bootstrap();

  runApp(
    MultiProvider(
      providers: [
        Provider<ApiService>.value(value: api),
        Provider<ApiClient>.value(value: client),
        ChangeNotifierProvider<SettingsProvider>.value(value: settings),
        ChangeNotifierProvider<AuthProvider>.value(value: auth),
        ChangeNotifierProvider<ChatProvider>.value(value: chat),
      ],
      child: const VidhikApp(),
    ),
  );
}
