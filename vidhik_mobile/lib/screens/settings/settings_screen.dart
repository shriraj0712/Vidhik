import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/config/app_config.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/format.dart';
import '../../providers/auth_provider.dart';
import '../../providers/chat_provider.dart';
import '../../providers/settings_provider.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _urlController;
  bool _testing = false;
  String? _testResult;
  bool _testOk = false;

  @override
  void initState() {
    super.initState();
    _urlController = TextEditingController(
      text: context.read<SettingsProvider>().baseUrl,
    );
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _saveUrl() async {
    final settings = context.read<SettingsProvider>();
    final ok = await settings.setBaseUrl(_urlController.text);
    if (!mounted) return;
    if (!ok) {
      setState(() {
        _testOk = false;
        _testResult = 'Enter a valid http:// or https:// URL with a host.';
      });
      return;
    }
    _urlController.text = settings.baseUrl;
    setState(() {
      _testResult = null;
      _testOk = false;
    });
    showInfoSnack(context, 'Backend URL saved.');
  }

  Future<void> _testConnection() async {
    setState(() {
      _testing = true;
      _testResult = null;
    });
    try {
      final health = await context.read<ApiService>().health();
      final database = asMap(health['database']);
      final parts = <String>[
        firstNonEmpty([health['status'], 'unknown']),
        if (asString(database['status']).isNotEmpty)
          'database ${database['status']}',
      ];
      if (!mounted) return;
      setState(() {
        _testOk = true;
        _testResult = 'Connected: ${parts.join(' · ')}';
      });
    } on Exception catch (e) {
      if (!mounted) return;
      setState(() {
        _testOk = false;
        _testResult = '$e'.replaceFirst('ApiException: ', '');
      });
    } finally {
      if (mounted) {
        setState(() {
          _testing = false;
        });
      }
    }
  }

  Future<void> _signOut() async {
    final ok = await confirmDialog(
      context,
      title: 'Sign out of VIDHIK?',
      message: 'This device will be signed out. Your data remains protected on the server.',
      confirmLabel: 'Sign out',
      destructive: true,
    );
    if (!ok || !mounted) return;
    context.read<ChatProvider>().clear();
    await context.read<AuthProvider>().logout();
    if (!mounted) return;
    Navigator.of(context).popUntil((route) => route.isFirst);
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsProvider>();
    final auth = context.watch<AuthProvider>();
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
        children: [
          const SectionTitle(
            'Backend connection',
            subtitle: 'Required for every API call. Point this at your Vidhik FastAPI server.',
          ),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextField(
                  controller: _urlController,
                  keyboardType: TextInputType.url,
                  autocorrect: false,
                  decoration: const InputDecoration(
                    labelText: 'API base URL',
                    hintText: 'https://api.example.com',
                    prefixIcon: Icon(Icons.dns_outlined),
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Default for this build: ${AppConfig.defaultBaseUrl}',
                  style: const TextStyle(
                    fontSize: 10.5,
                    color: AppColors.muted,
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: FilledButton.icon(
                        onPressed: _saveUrl,
                        icon: const Icon(Icons.save_outlined, size: 18),
                        label: const Text('Save URL'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _testing ? null : _testConnection,
                        icon: _testing
                            ? const SizedBox(
                                width: 15,
                                height: 15,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.wifi_tethering, size: 18),
                        label: const Text('Test'),
                      ),
                    ),
                  ],
                ),
                if (_testResult != null) ...[
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: (_testOk ? AppColors.success : AppColors.danger)
                          .withValues(alpha: 0.07),
                      borderRadius: BorderRadius.circular(9),
                    ),
                    child: Text(
                      _testResult!,
                      style: TextStyle(
                        fontSize: 11.5,
                        height: 1.4,
                        color: _testOk ? AppColors.success : AppColors.danger,
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: 6),
                TextButton.icon(
                  onPressed: () async {
                    await settings.resetBaseUrl();
                    if (!mounted) return;
                    _urlController.text = settings.baseUrl;
                    showInfoSnack(context, 'Reset to the compiled default.');
                  },
                  icon: const Icon(Icons.restore, size: 16),
                  label: const Text('Reset to default'),
                ),
                const Text(
                  'On an Android emulator the host machine is 10.0.2.2. On a physical phone use your '
                  'computer’s LAN address (for example http://192.168.1.10:8000) and ensure uvicorn is '
                  'bound to 0.0.0.0. Cleartext HTTP is enabled for development only.',
                  style: TextStyle(
                    fontSize: 10.5,
                    color: AppColors.muted,
                    height: 1.45,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          const SectionTitle('Language'),
          AppCard(
            child: Column(
              children: [
                for (final entry in SettingsProvider.languageNames.entries)
                  RadioListTile<String>(
                    contentPadding: EdgeInsets.zero,
                    value: entry.key,
                    groupValue: settings.language,
                    title: Text(
                      entry.value,
                      style: const TextStyle(fontSize: 13.5),
                    ),
                    subtitle: entry.key == 'en'
                        ? null
                        : const Text(
                            'Applied to AI answers, legal tools and complaint drafts',
                            style: TextStyle(
                              fontSize: 10.5,
                              color: AppColors.muted,
                            ),
                          ),
                    onChanged: (value) async {
                      if (value == null) return;
                      await settings.setLanguage(value);
                      if (mounted) {
                        context.read<ChatProvider>().setLanguage(value);
                      }
                    },
                  ),
                const Padding(
                  padding: EdgeInsets.only(top: 4),
                  child: Text(
                    'Navigation and system labels remain in English in this release.',
                    style: TextStyle(fontSize: 10.5, color: AppColors.muted),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          const SectionTitle('Appearance'),
          AppCard(
            child: Column(
              children: [
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  value: settings.themeMode == ThemeMode.dark,
                  title: const Text(
                    'Dark theme',
                    style: TextStyle(fontSize: 13.5),
                  ),
                  subtitle: const Text(
                    'Match the device or force light mode',
                    style: TextStyle(fontSize: 10.5, color: AppColors.muted),
                  ),
                  onChanged: (value) {
                    settings.setThemeMode(
                      value ? ThemeMode.dark : ThemeMode.light,
                    );
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          const SectionTitle('Account'),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                InfoRow('Signed in as', auth.user?.email ?? '—'),
                InfoRow('Role', auth.user?.displayRole ?? '—'),
                InfoRow(
                  '2FA',
                  auth.user?.twoFactorEnabled == true
                      ? 'Enabled'
                      : 'Not enabled',
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.danger,
                  ),
                  onPressed: _signOut,
                  icon: const Icon(Icons.logout, size: 18),
                  label: const Text('Sign out'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'About VIDHIK',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                ),
                const SizedBox(height: 6),
                const Text(
                  'VIDHIK AI is an Indian legal research and awareness platform. It retrieves statutory provisions '
                  'from its own database and does not generate legal answers without grounding. It is not a law firm '
                  'and does not provide legal representation.',
                  style: TextStyle(
                    fontSize: 11.5,
                    color: AppColors.muted,
                    height: 1.45,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Version ${AppConfig.version}',
                  style: const TextStyle(
                    fontSize: 10.5,
                    color: AppColors.muted,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
