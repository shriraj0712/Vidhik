import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/format.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';

class SecurityScreen extends StatefulWidget {
  const SecurityScreen({super.key});

  @override
  State<SecurityScreen> createState() => _SecurityScreenState();
}

class _SecurityScreenState extends State<SecurityScreen> {
  late Future<List<Map<String, dynamic>>> _sessionsFuture;
  late Future<Map<String, dynamic>> _alertsFuture;

  final _currentPassword = TextEditingController();
  final _newPassword = TextEditingController();
  final _confirmPassword = TextEditingController();
  bool _passwordBusy = false;
  String? _passwordError;

  @override
  void initState() {
    super.initState();
    final api = context.read<ApiService>();
    _sessionsFuture = api.sessions();
    _alertsFuture = api.securityAlerts();
  }

  @override
  void dispose() {
    _currentPassword.dispose();
    _newPassword.dispose();
    _confirmPassword.dispose();
    super.dispose();
  }

  Future<void> _reload() async {
    final api = context.read<ApiService>();
    setState(() {
      _sessionsFuture = api.sessions();
      _alertsFuture = api.securityAlerts();
    });
    await Future.wait([_sessionsFuture, _alertsFuture]);
  }

  Future<void> _revoke(int sessionId) async {
    final ok = await confirmDialog(
      context,
      title: 'Sign out this device?',
      message: 'The selected session will be revoked immediately.',
      confirmLabel: 'Revoke',
      destructive: true,
    );
    if (!ok) return;
    try {
      await context.read<ApiService>().revokeSession(sessionId);
      if (!mounted) return;
      await _reload();
      if (mounted) showInfoSnack(context, 'Session revoked.');
    } on Exception catch (e) {
      if (mounted) showErrorSnack(context, e);
    }
  }

  Future<void> _revokeOthers() async {
    final ok = await confirmDialog(
      context,
      title: 'Sign out all other devices?',
      message: 'Every active session except this device will be revoked.',
      confirmLabel: 'Sign out others',
      destructive: true,
    );
    if (!ok) return;
    try {
      final result = await context.read<ApiService>().revokeOtherSessions();
      if (!mounted) return;
      await _reload();
      if (mounted) {
        showInfoSnack(
          context,
          '${result['message'] ?? 'Other sessions have been signed out.'}',
        );
      }
    } on Exception catch (e) {
      if (mounted) showErrorSnack(context, e);
    }
  }

  Future<void> _markAlertRead(int alertId) async {
    try {
      await context.read<ApiService>().markSecurityAlertRead(alertId);
      await _reload();
    } on Exception catch (e) {
      if (mounted) showErrorSnack(context, e);
    }
  }

  Future<void> _changePassword() async {
    if (_currentPassword.text.isEmpty) {
      setState(() {
        _passwordError = 'Enter your current password.';
      });
      return;
    }
    if (_newPassword.text.length < 8 ||
        !RegExp(r'[A-Z]').hasMatch(_newPassword.text) ||
        !RegExp(r'[a-z]').hasMatch(_newPassword.text) ||
        !RegExp(r'[0-9]').hasMatch(_newPassword.text) ||
        !RegExp(r'[^A-Za-z0-9]').hasMatch(_newPassword.text)) {
      setState(
        () => _passwordError = 'New password needs 8+ characters with upper, lower, number and symbol.',
      );
      return;
    }
    if (_newPassword.text != _confirmPassword.text) {
      setState(() {
        _passwordError = 'New passwords do not match.';
      });
      return;
    }
    setState(() {
      _passwordBusy = true;
      _passwordError = null;
    });
    try {
      await context.read<ApiService>().changePassword(
        currentPassword: _currentPassword.text,
        newPassword: _newPassword.text,
        confirmPassword: _confirmPassword.text,
      );
      if (!mounted) return;
      _currentPassword.clear();
      _newPassword.clear();
      _confirmPassword.clear();
      showInfoSnack(context, 'Password changed successfully.');
    } on Exception catch (e) {
      if (!mounted) return;
      setState(() {
        _passwordError = '$e'.replaceFirst('ApiException: ', '');
      });
    } finally {
      if (mounted) {
        setState(() {
          _passwordBusy = false;
        });
      }
    }
  }

  Future<void> _regenerateRecoveryCodes() async {
    final password = TextEditingController();
    final totp = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Regenerate recovery codes'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Confirm your identity. Provide your current password and/or a valid authenticator code.',
              style: TextStyle(fontSize: 12.5, height: 1.4),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: password,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'Current password'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: totp,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Authenticator code',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Generate'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    try {
      final result = await context.read<ApiService>().regenerateRecoveryCodes(
        password: password.text.isEmpty ? null : password.text,
        totpCode: totp.text.isEmpty ? null : totp.text,
      );
      if (!mounted) return;
      final codes = asMapList(result['recovery_codes']);
      final list = codes.isEmpty
          ? asMapList(result['codes']).map((e) => asString(e)).toList()
          : codes.map((e) => asString(e)).where((e) => e.isNotEmpty).toList();
      if (list.isEmpty) {
        final raw = result['recovery_codes'];
        if (raw is List) {
          list.addAll(raw.map((e) => asString(e)).where((e) => e.isNotEmpty));
        }
      }
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('New recovery codes'),
          content: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Store these codes securely. Each code works once.',
                  style: TextStyle(fontSize: 12),
                ),
                const SizedBox(height: 12),
                for (final code in list)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 5),
                    child: Text(
                      code,
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        fontWeight: FontWeight.w600,
                        fontSize: 12.5,
                      ),
                    ),
                  ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () {
                Clipboard.setData(ClipboardData(text: list.join('\n')));
                Navigator.pop(context);
                showInfoSnack(this.context, 'Recovery codes copied.');
              },
              child: const Text('Copy all'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Done'),
            ),
          ],
        ),
      );
    } on Exception catch (e) {
      if (mounted) showErrorSnack(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Security & activity'),
        actions: [
          IconButton(onPressed: _reload, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
          children: [
            AppCard(
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppColors.success.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(
                      Icons.verified_user,
                      color: AppColors.success,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Mandatory 2FA is active',
                          style: TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 14,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${auth.user?.email ?? ''} · ${auth.user?.accountStatus ?? 'active'}',
                          style: const TextStyle(
                            fontSize: 11.5,
                            color: AppColors.muted,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            SectionTitle(
              'Active sessions',
              action: TextButton(
                onPressed: _revokeOthers,
                child: const Text('Sign out others'),
              ),
            ),
            FutureBuilder<List<Map<String, dynamic>>>(
              future: _sessionsFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Padding(
                    padding: EdgeInsets.all(16),
                    child: Center(
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                  );
                }
                if (snapshot.hasError) {
                  return AppCard(
                    child: Text(
                      '${snapshot.error}'.replaceFirst('ApiException: ', ''),
                      style: const TextStyle(fontSize: 12),
                    ),
                  );
                }
                final sessions = snapshot.data ?? const [];
                if (sessions.isEmpty) {
                  return const AppCard(
                    child: Text(
                      'No active sessions reported.',
                      style: TextStyle(color: AppColors.muted),
                    ),
                  );
                }
                return Column(
                  children: [
                    for (final session in sessions)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: AppCard(
                          child: Row(
                            children: [
                              Icon(
                                asString(session['device'])
                                        .toLowerCase()
                                        .contains('mobile')
                                    ? Icons.smartphone
                                    : Icons.computer,
                                color: AppColors.teal,
                                size: 20,
                              ),
                              const SizedBox(width: 11),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      '${firstNonEmpty([session['browser'], 'Browser'])} on '
                                      '${firstNonEmpty([session['os'], 'Device'])}',
                                      style: const TextStyle(
                                        fontWeight: FontWeight.w600,
                                        fontSize: 12.5,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      [
                                        firstNonEmpty([
                                          session['ip_address'],
                                          '',
                                        ]),
                                        firstNonEmpty([
                                          session['location'],
                                          '',
                                        ]),
                                        firstNonEmpty([
                                          session['login_method'],
                                          '',
                                        ]),
                                      ].where((e) => e.isNotEmpty).join(' · '),
                                      style: const TextStyle(
                                        fontSize: 10.5,
                                        color: AppColors.muted,
                                      ),
                                    ),
                                    Text(
                                      'Signed in ${formatDateTime(session['created_at'])}',
                                      style: const TextStyle(
                                        fontSize: 10.5,
                                        color: AppColors.muted,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              if (session['is_current'] == true)
                                const Tag(
                                  'This device',
                                  color: AppColors.success,
                                )
                              else
                                IconButton(
                                  tooltip: 'Revoke session',
                                  onPressed: () =>
                                      _revoke(asInt(session['session_id'])),
                                  icon: const Icon(
                                    Icons.logout,
                                    size: 18,
                                    color: AppColors.danger,
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ),
                  ],
                );
              },
            ),
            const SizedBox(height: 16),
            const SectionTitle('Change password'),
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (_passwordError != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Text(
                        _passwordError!,
                        style: const TextStyle(
                          color: AppColors.danger,
                          fontSize: 12,
                          height: 1.4,
                        ),
                      ),
                    ),
                  TextField(
                    controller: _currentPassword,
                    obscureText: true,
                    decoration: const InputDecoration(
                      labelText: 'Current password',
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _newPassword,
                    obscureText: true,
                    decoration: const InputDecoration(
                      labelText: 'New password',
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _confirmPassword,
                    obscureText: true,
                    decoration: const InputDecoration(
                      labelText: 'Confirm new password',
                    ),
                  ),
                  const SizedBox(height: 12),
                  FilledButton(
                    onPressed: _passwordBusy ? null : _changePassword,
                    child: _passwordBusy
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2.2,
                              color: Colors.white,
                            ),
                          )
                        : const Text('Update password'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            SectionTitle(
              'Security alerts',
              action: TextButton(
                onPressed: _regenerateRecoveryCodes,
                child: const Text('Recovery codes'),
              ),
            ),
            FutureBuilder<Map<String, dynamic>>(
              future: _alertsFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Padding(
                    padding: EdgeInsets.all(16),
                    child: Center(
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                  );
                }
                if (snapshot.hasError) {
                  return AppCard(
                    child: Text(
                      '${snapshot.error}'.replaceFirst('ApiException: ', ''),
                      style: const TextStyle(fontSize: 12),
                    ),
                  );
                }
                final alerts = asMapList(asMap(snapshot.data)['alerts']);
                if (alerts.isEmpty) {
                  return const AppCard(
                    child: Text(
                      'No security incidents recorded.',
                      style: TextStyle(color: AppColors.muted),
                    ),
                  );
                }
                return Column(
                  children: [
                    for (final alert in alerts)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: AppCard(
                          onTap: () => _markAlertRead(asInt(alert['alert_id'])),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      firstNonEmpty([
                                        alert['title'],
                                        'Security alert',
                                      ]),
                                      style: const TextStyle(
                                        fontWeight: FontWeight.w600,
                                        fontSize: 13,
                                      ),
                                    ),
                                  ),
                                  Tag(
                                    firstNonEmpty([alert['severity'], 'info'])
                                        .toUpperCase(),
                                    color: AppColors.riskColor(
                                      firstNonEmpty([alert['severity'], '']),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 3),
                              Text(
                                asString(alert['description']),
                                style: const TextStyle(
                                  fontSize: 12,
                                  height: 1.4,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                formatDateTime(alert['created_at']),
                                style: const TextStyle(
                                  fontSize: 10.5,
                                  color: AppColors.muted,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
