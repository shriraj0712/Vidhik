import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/theme/app_theme.dart';
import 'providers/auth_provider.dart';
import 'providers/settings_provider.dart';
import 'screens/auth/auth_screen.dart';
import 'screens/home_shell.dart';
import 'screens/splash_screen.dart';

class VidhikApp extends StatelessWidget {
  const VidhikApp({super.key});

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsProvider>();
    return MaterialApp(
      title: 'VIDHIK AI',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: settings.themeMode,
      home: const _RootGate(),
    );
  }
}

class _RootGate extends StatelessWidget {
  const _RootGate();

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    switch (auth.status) {
      case AuthStatus.booting:
        return const SplashScreen();
      case AuthStatus.signedOut:
        return AuthScreen(sessionNotice: auth.sessionNotice);
      case AuthStatus.signedIn:
        return const HomeShell();
    }
  }
}

/// Shared navy gradient used by authentication and splash surfaces.
class BrandGradient extends StatelessWidget {
  const BrandGradient({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.navyDeep, AppColors.navy, Color(0xFF145C66)],
        ),
      ),
      child: child,
    );
  }
}
