import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/format.dart';
import '../../models/citizen.dart';
import '../../providers/auth_provider.dart';
import '../../providers/settings_provider.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';
import '../security/security_screen.dart';
import '../settings/settings_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  late Future<CitizenProfile>? _future;

  final _fullName = TextEditingController();
  final _phone = TextEditingController();
  final _dob = TextEditingController();
  final _address = TextEditingController();
  final _city = TextEditingController();
  final _state = TextEditingController();
  final _pincode = TextEditingController();
  final _occupation = TextEditingController();
  final _emergency = TextEditingController();
  String _language = 'en';

  bool _initialised = false;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final auth = context.read<AuthProvider>();
    if (!auth.isLawyer) {
      _future = context.read<ApiService>().citizenProfile();
      _future!.then(_fill).catchError((_) {});
    }
  }

  void _fill(CitizenProfile profile) {
    if (!mounted) return;
    setState(() {
      _fullName.text = profile.fullName;
      _phone.text = profile.phone ?? '';
      _dob.text = profile.dateOfBirth ?? '';
      _address.text = profile.address ?? '';
      _city.text = profile.city ?? '';
      _state.text = profile.state ?? '';
      _pincode.text = profile.pincode ?? '';
      _occupation.text = profile.occupation ?? '';
      _emergency.text = profile.emergencyContact ?? '';
      _language = profile.preferredLanguage;
      _initialised = true;
    });
  }

  @override
  void dispose() {
    _fullName.dispose();
    _phone.dispose();
    _dob.dispose();
    _address.dispose();
    _city.dispose();
    _state.dispose();
    _pincode.dispose();
    _occupation.dispose();
    _emergency.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_fullName.text.trim().length < 2) {
      setState(() {
        _error = 'Enter your full name.';
      });
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final updated = await context.read<ApiService>().updateCitizenProfile({
        'full_name': _fullName.text.trim(),
        'phone': _phone.text.trim().isEmpty ? null : _phone.text.trim(),
        'date_of_birth': _dob.text.trim().isEmpty ? null : _dob.text.trim(),
        'address': _address.text.trim().isEmpty ? null : _address.text.trim(),
        'city': _city.text.trim().isEmpty ? null : _city.text.trim(),
        'state': _state.text.trim().isEmpty ? null : _state.text.trim(),
        'pincode': _pincode.text.trim().isEmpty ? null : _pincode.text.trim(),
        'occupation': _occupation.text.trim().isEmpty
            ? null
            : _occupation.text.trim(),
        'emergency_contact': _emergency.text.trim().isEmpty
            ? null
            : _emergency.text.trim(),
        'preferred_language': _language,
      });
      if (!mounted) return;
      _fill(updated);
      await context.read<AuthProvider>().refreshProfile();
      await context.read<SettingsProvider>().setLanguage(_language);
      if (mounted) showInfoSnack(context, 'Profile updated.');
    } on Exception catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e'.replaceFirst('ApiException: ', '');
      });
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final user = auth.user;
    final isLawyer = auth.isLawyer;

    return Scaffold(
      appBar: AppBar(title: const Text('Profile & account')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
        children: [
          AppCard(
            child: Row(
              children: [
                CircleAvatar(
                  radius: 28,
                  backgroundColor: AppColors.navy,
                  child: Text(
                    initialsOf(user?.safeName ?? 'V'),
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                      fontSize: 18,
                    ),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        user?.safeName ?? 'VIDHIK user',
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        user?.email ?? '',
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.muted,
                        ),
                      ),
                      const SizedBox(height: 5),
                      Row(
                        children: [
                          Tag(user?.displayRole ?? 'Citizen'),
                          const SizedBox(width: 6),
                          if (user?.twoFactorEnabled == true)
                            const Tag('2FA active', color: AppColors.success),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          if (isLawyer)
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Advocate workspace',
                    style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Professional profile, bar council details and practice information are managed in the lawyer workspace.',
                    style: TextStyle(
                      fontSize: 12.5,
                      color: AppColors.muted,
                      height: 1.45,
                    ),
                  ),
                  const SizedBox(height: 10),
                  OutlinedButton.icon(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.work_outline, size: 18),
                    label: const Text('Open lawyer workspace'),
                  ),
                ],
              ),
            )
          else
            FutureBuilder<CitizenProfile>(
              future: _future,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Padding(
                    padding: EdgeInsets.all(24),
                    child: Center(
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                  );
                }
                if (snapshot.hasError) {
                  return AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${snapshot.error}'.replaceFirst(
                            'ApiException: ',
                            '',
                          ),
                          style: const TextStyle(fontSize: 12.5),
                        ),
                        const SizedBox(height: 8),
                        TextButton(
                          onPressed: () => setState(() {
                            _future = context
                                .read<ApiService>()
                                .citizenProfile();
                            _future!.then(_fill).catchError((_) {});
                          }),
                          child: const Text('Retry'),
                        ),
                      ],
                    ),
                  );
                }
                if (!_initialised) {
                  // Fill after the first successful frame.
                  WidgetsBinding.instance.addPostFrameCallback((_) {
                    if (snapshot.hasData) _fill(snapshot.data!);
                  });
                }
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (_error != null)
                      Container(
                        margin: const EdgeInsets.only(bottom: 10),
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: AppColors.danger.withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(9),
                        ),
                        child: Text(
                          _error!,
                          style: const TextStyle(
                            color: AppColors.danger,
                            fontSize: 12,
                            height: 1.4,
                          ),
                        ),
                      ),
                    const SectionTitle('Personal details'),
                    TextField(
                      controller: _fullName,
                      textCapitalization: TextCapitalization.words,
                      decoration: const InputDecoration(labelText: 'Full name'),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _phone,
                      keyboardType: TextInputType.phone,
                      decoration: const InputDecoration(
                        labelText: 'Mobile number',
                      ),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _dob,
                      decoration: const InputDecoration(
                        labelText: 'Date of birth',
                        hintText: 'YYYY-MM-DD',
                      ),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _address,
                      minLines: 2,
                      maxLines: 4,
                      decoration: const InputDecoration(
                        labelText: 'Address',
                        alignLabelWithHint: true,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _city,
                            decoration: const InputDecoration(
                              labelText: 'City',
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: TextField(
                            controller: _state,
                            decoration: const InputDecoration(
                              labelText: 'State',
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _pincode,
                            keyboardType: TextInputType.number,
                            decoration: const InputDecoration(
                              labelText: 'PIN code',
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: TextField(
                            controller: _occupation,
                            decoration: const InputDecoration(
                              labelText: 'Occupation',
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _emergency,
                      decoration: const InputDecoration(
                        labelText: 'Emergency contact',
                      ),
                    ),
                    const SizedBox(height: 10),
                    DropdownButtonFormField<String>(
                      initialValue: _language,
                      decoration: const InputDecoration(
                        labelText: 'Preferred language',
                      ),
                      items: [
                        for (final entry
                            in SettingsProvider.languageNames.entries)
                          DropdownMenuItem(
                            value: entry.key,
                            child: Text(entry.value),
                          ),
                      ],
                      onChanged: (value) =>
                          setState(() => _language = value ?? 'en'),
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: _busy || !_initialised ? null : _save,
                      child: _busy
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2.2,
                                color: Colors.white,
                              ),
                            )
                          : const Text('Save profile'),
                    ),
                  ],
                );
              },
            ),
          const SizedBox(height: 20),
          const SectionTitle('Account security'),
          AppCard(
            child: Column(
              children: [
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(
                    Icons.shield_outlined,
                    color: AppColors.teal,
                  ),
                  title: const Text(
                    'Security & active sessions',
                    style: TextStyle(fontSize: 13.5),
                  ),
                  subtitle: const Text(
                    'Devices, alerts and password',
                    style: TextStyle(fontSize: 11, color: AppColors.muted),
                  ),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const SecurityScreen()),
                  ),
                ),
                const Divider(height: 1),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(
                    Icons.settings_outlined,
                    color: AppColors.teal,
                  ),
                  title: const Text(
                    'App settings',
                    style: TextStyle(fontSize: 13.5),
                  ),
                  subtitle: const Text(
                    'Backend URL, language and theme',
                    style: TextStyle(fontSize: 11, color: AppColors.muted),
                  ),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const SettingsScreen()),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Text(
            'Account created ${formatDate(user?.accountStatus)}'.replaceAll(
              'created active',
              'active',
            ),
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 10.5, color: AppColors.muted),
          ),
        ],
      ),
    );
  }
}
