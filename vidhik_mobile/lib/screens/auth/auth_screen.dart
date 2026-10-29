import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../app.dart';
import '../../core/network/api_client.dart';
import '../../core/theme/app_theme.dart';
import '../../models/auth_user.dart';
import '../../providers/auth_provider.dart';
import '../../providers/settings_provider.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';
import '../../widgets/turnstile_dialog.dart';

enum _AuthStep {
  login,
  register,
  verifyOtp,
  setup2fa,
  recoveryCodes,
  twoFactorLogin,
}

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key, this.sessionNotice});

  final String? sessionNotice;

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  _AuthStep _step = _AuthStep.login;
  final _loginForm = GlobalKey<FormState>();
  final _registerForm = GlobalKey<FormState>();

  final _identifier = TextEditingController();
  final _loginPassword = TextEditingController();
  final _fullName = TextEditingController();
  final _email = TextEditingController();
  final _phone = TextEditingController();
  final _registerPassword = TextEditingController();
  final _confirmPassword = TextEditingController();
  final _otp = TextEditingController();
  final _totp = TextEditingController();

  bool _obscureLogin = true;
  bool _obscureRegister = true;
  bool _obscureConfirm = true;
  bool _busy = false;
  String? _error;

  bool _captchaEnabled = false;
  bool _configLoaded = false;
  bool _configLoadFailed = false;

  bool get _showCaptchaNotice =>
      !_captchaEnabled && (_configLoaded || _configLoadFailed);
  String _turnstileSiteKey = '';
  String? _captchaToken;

  String _registrationTarget = '';
  String _maskedDestination = '';
  TwoFactorEnrollment? _enrollment;
  List<String> _recoveryCodes = const [];
  String? _pendingTwoFactorToken;
  bool _useRecoveryCode = false;

  Timer? _resendTimer;
  int _resendSeconds = 0;

  @override
  void initState() {
    super.initState();
    _loadAuthConfig();
  }

  @override
  void dispose() {
    _resendTimer?.cancel();
    _identifier.dispose();
    _loginPassword.dispose();
    _fullName.dispose();
    _email.dispose();
    _phone.dispose();
    _registerPassword.dispose();
    _confirmPassword.dispose();
    _otp.dispose();
    _totp.dispose();
    super.dispose();
  }

  Future<void> _loadAuthConfig() async {
    final api = context.read<ApiService>();
    try {
      final config = await api.turnstileConfig();
      if (!mounted) return;
      setState(() {
        _turnstileSiteKey = '${config['site_key'] ?? ''}';
        _captchaEnabled =
            config['enabled'] == true && _turnstileSiteKey.isNotEmpty;
        _configLoaded = true;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _configLoaded = true;
        _configLoadFailed = true;
        _captchaEnabled = false;
      });
    }
  }

  void _switchStep(_AuthStep step) {
    setState(() {
      _step = step;
      _error = null;
      _totp.clear();
      _otp.clear();
    });
  }

  Future<String?> _obtainCaptcha() async {
    if (!_configLoaded) {
      await _loadAuthConfig();
      if (!mounted) return null;
    }
    if (!_captchaEnabled) return null;
    if (_captchaToken != null && _captchaToken!.isNotEmpty) {
      return _captchaToken;
    }

    final settings = context.read<SettingsProvider>();
    final token = await TurnstileDialog.show(
      context,
      siteKey: _turnstileSiteKey,
      baseUrl: settings.baseUrl,
    );
    if (!mounted) return null;
    if (token != null && token.isNotEmpty) {
      setState(() {
        _captchaToken = token;
      });
      return token;
    }
    return null;
  }

  // -------------------------------------------------------------------
  // Login
  // -------------------------------------------------------------------

  Future<void> _submitLogin() async {
    if (!(_loginForm.currentState?.validate() ?? false)) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final captcha = await _obtainCaptcha();
      if (!mounted) return;
      if (_captchaEnabled && captcha == null) {
        throw const ApiException(
          'Complete the security verification to continue.',
        );
      }
      final auth = context.read<AuthProvider>();
      final challenge = await auth.login(
        identifier: _identifier.text,
        password: _loginPassword.text,
        turnstileToken: captcha,
      );
      if (!mounted) return;
      final message = challenge.message ?? '';
      if (!challenge.requiresTwoFactor) {
        throw ApiException(
          message.isNotEmpty ? message : 'This account cannot start a two-factor challenge. Contact support.',
        );
      }
      setState(() {
        _pendingTwoFactorToken = challenge.twoFactorToken;
        _step = _AuthStep.twoFactorLogin;
        _useRecoveryCode = false;
      });
    } on ApiException catch (e) {
      setState(() {
        _error = e.message;
        _captchaToken = null;
      });
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  Future<void> _submitLoginTwoFactor() async {
    final code = _totp.text.trim();
    if (code.isEmpty) {
      setState(() {
        _error = 'Enter the code from your authenticator app.';
      });
      return;
    }
    if (_pendingTwoFactorToken == null) {
      setState(() {
        _error = 'The two-factor challenge expired. Sign in again.';
      });
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await context.read<AuthProvider>().verifyLogin(
        twoFactorToken: _pendingTwoFactorToken!,
        code: code,
        useRecoveryCode: _useRecoveryCode,
      );
      // Root gate switches to the workspace when authentication succeeds.
    } on ApiException catch (e) {
      setState(() {
        _error = e.message;
      });
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  // -------------------------------------------------------------------
  // Registration
  // -------------------------------------------------------------------

  bool _isStrongPassword(String value) {
    return value.length >= 8 &&
        RegExp(r'[A-Z]').hasMatch(value) &&
        RegExp(r'[a-z]').hasMatch(value) &&
        RegExp(r'[0-9]').hasMatch(value) &&
        RegExp(r'[^A-Za-z0-9]').hasMatch(value);
  }

  Future<void> _submitRegistration() async {
    if (!(_registerForm.currentState?.validate() ?? false)) return;
    if (!_isStrongPassword(_registerPassword.text)) {
      setState(
        () => _error = 'Password must be at least 8 characters and include uppercase, lowercase, a number and a special character.',
      );
      return;
    }
    if (_registerPassword.text != _confirmPassword.text) {
      setState(() {
        _error = 'Passwords do not match.';
      });
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final captcha = await _obtainCaptcha();
      if (!mounted) return;
      if (_captchaEnabled && captcha == null) {
        throw const ApiException(
          'Complete the security verification to continue.',
        );
      }
      final auth = context.read<AuthProvider>();
      final result = await auth.registerInitiate(
        fullName: _fullName.text,
        email: _email.text,
        password: _registerPassword.text,
        confirmPassword: _confirmPassword.text,
        phone: _phone.text,
        turnstileToken: captcha,
      );
      if (!mounted) return;
      setState(() {
        _registrationTarget = result.target.isNotEmpty
            ? result.target
            : _email.text.trim();
        _maskedDestination = result.maskedDestination.isNotEmpty
            ? result.maskedDestination
            : result.target;
        _step = _AuthStep.verifyOtp;
        _captchaToken = null;
        _startResendCountdown(result.resendCooldownSeconds);
      });
      showInfoSnack(
        context,
        result.message.isNotEmpty ? result.message : 'Verification code sent.',
      );
    } on ApiException catch (e) {
      setState(() {
        _error = e.message;
        _captchaToken = null;
      });
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  void _startResendCountdown(int seconds) {
    _resendTimer?.cancel();
    _resendSeconds = seconds;
    _resendTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      if (_resendSeconds <= 1) {
        timer.cancel();
        setState(() {
          _resendSeconds = 0;
        });
      } else {
        setState(() => _resendSeconds -= 1);
      }
    });
  }

  Future<void> _verifySignupOtp() async {
    final code = _otp.text.trim();
    if (code.length != 6 || int.tryParse(code) == null) {
      setState(() {
        _error = 'Enter the 6-digit code sent to you.';
      });
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final enrollment = await context.read<AuthProvider>().verifySignupOtp(
        target: _registrationTarget,
        otpCode: code,
      );
      if (!mounted) return;
      setState(() {
        _enrollment = enrollment;
        _step = _AuthStep.setup2fa;
      });
    } on ApiException catch (e) {
      setState(() {
        _error = e.message;
      });
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  Future<void> _resendOtp() async {
    if (_resendSeconds > 0) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final api = context.read<ApiService>();
      await api.resendOtp(target: _registrationTarget);
      if (!mounted) return;
      setState(() => _startResendCountdown(60));
      showInfoSnack(context, 'A new verification code has been sent.');
    } on ApiException catch (e) {
      setState(() {
        _error = e.message;
      });
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  Future<void> _completeTwoFactorSetup() async {
    final code = _totp.text.trim();
    if (code.length != 6 || int.tryParse(code) == null) {
      setState(() {
        _error = 'Enter the 6-digit code from your authenticator app.';
      });
      return;
    }
    if (_enrollment == null) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final session = await context.read<AuthProvider>().completeTwoFactorSetup(
        setupToken: _enrollment!.setupToken,
        totpCode: code,
      );
      if (!mounted) return;
      setState(() {
        _recoveryCodes = session.recoveryCodes;
        _step = _AuthStep.recoveryCodes;
      });
    } on ApiException catch (e) {
      setState(() {
        _error = e.message;
      });
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  // -------------------------------------------------------------------
  // Build
  // -------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: BrandGradient(
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 28, 20, 28),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _brandHeader(),
                const SizedBox(height: 24),
                Container(
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surface,
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.18),
                        blurRadius: 26,
                        offset: const Offset(0, 12),
                      ),
                    ],
                  ),
                  padding: const EdgeInsets.fromLTRB(20, 22, 20, 22),
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 220),
                    child: KeyedSubtree(
                      key: ValueKey(_step),
                      child: _buildStep(),
                    ),
                  ),
                ),
                const SizedBox(height: 18),
                _footerNote(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _brandHeader() {
    return Column(
      children: [
        Container(
          width: 66,
          height: 66,
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.08),
            shape: BoxShape.circle,
            border: Border.all(color: Colors.white.withValues(alpha: 0.22)),
          ),
          child: const Icon(
            Icons.account_balance_rounded,
            color: Colors.white,
            size: 34,
          ),
        ),
        const SizedBox(height: 12),
        const Text(
          'VIDHIK AI',
          style: TextStyle(
            color: Colors.white,
            fontSize: 25,
            fontWeight: FontWeight.w800,
            letterSpacing: 2.6,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          'Know your rights. Understand the law.',
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.78),
            fontSize: 12.5,
          ),
        ),
      ],
    );
  }

  Widget _footerNote() {
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.lock_outline,
              size: 14,
              color: Colors.white.withValues(alpha: 0.75),
            ),
            const SizedBox(width: 6),
            Text(
              'Mandatory 2FA · bcrypt hashing · JWT sessions',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.75),
                fontSize: 11,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Text(
          'TLS-encrypted in production. VIDHIK provides legal awareness, not legal representation.',
          textAlign: TextAlign.center,
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.55),
            fontSize: 10.5,
            height: 1.4,
          ),
        ),
      ],
    );
  }

  Widget _buildStep() {
    switch (_step) {
      case _AuthStep.login:
        return _buildLogin();
      case _AuthStep.register:
        return _buildRegister();
      case _AuthStep.verifyOtp:
        return _buildVerifyOtp();
      case _AuthStep.setup2fa:
        return _buildSetup2fa();
      case _AuthStep.recoveryCodes:
        return _buildRecoveryCodes();
      case _AuthStep.twoFactorLogin:
        return _buildLoginTwoFactor();
    }
  }

  Widget _errorBanner() {
    final notice = widget.sessionNotice;
    final message = _error;
    if (message == null) {
      if (_step == _AuthStep.login && notice != null) {
        return _banner(notice, AppColors.warning);
      }
      return const SizedBox.shrink();
    }
    return _banner(message, AppColors.danger);
  }

  Widget _banner(String message, Color color) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline, size: 17, color: color),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: TextStyle(fontSize: 12.5, color: color, height: 1.4),
            ),
          ),
        ],
      ),
    );
  }

  Widget _modeTabs() {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Expanded(child: _modeTab('Sign in', _AuthStep.login)),
          Expanded(child: _modeTab('Create account', _AuthStep.register)),
        ],
      ),
    );
  }

  Widget _modeTab(String label, _AuthStep target) {
    final selected = _step == target;
    return GestureDetector(
      onTap: _busy ? null : () => _switchStep(target),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: selected ? Colors.white : Colors.transparent,
          borderRadius: BorderRadius.circular(9),
          boxShadow: selected
              ? [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.06),
                    blurRadius: 6,
                    offset: const Offset(0, 2),
                  ),
                ]
              : null,
        ),
        child: Text(
          label,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontWeight: FontWeight.w600,
            fontSize: 13.5,
            color: selected ? AppColors.navy : AppColors.muted,
          ),
        ),
      ),
    );
  }

  Widget _captchaButton() {
    final done = _captchaToken != null;
    if (done) {
      return OutlinedButton.icon(
        onPressed: _busy
            ? null
            : () async {
                setState(() {
                  _captchaToken = null;
                });
                await _obtainCaptcha();
              },
        icon: Icon(Icons.verified, size: 18),
        label: const Text('Human verification complete'),
      );
    }
    if (_configLoadFailed) {
      return Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: AppColors.danger.withValues(alpha: 0.07),
          borderRadius: BorderRadius.circular(10),
        ),
        child: const Text(
          'Could not reach the server to load the CAPTCHA settings. Check your internet connection and the backend URL in Settings.',
          style: TextStyle(
            fontSize: 11.5,
            color: AppColors.danger,
            height: 1.4,
          ),
        ),
      );
    }
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppColors.warning.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
      ),
      child: const Text(
        'CAPTCHA is not configured on this server build. Registration and sign-in may be rejected by the backend until Turnstile keys are set.',
        style: TextStyle(
          fontSize: 11.5,
          color: AppColors.warning,
          height: 1.4,
        ),
      ),
    );
  }

  Widget _buildLogin() {
    return Form(
      key: _loginForm,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _modeTabs(),
          const SizedBox(height: 18),
          _errorBanner(),
          TextFormField(
            controller: _identifier,
            keyboardType: TextInputType.emailAddress,
            textInputAction: TextInputAction.next,
            autofillHints: const [AutofillHints.email],
            decoration: const InputDecoration(
              labelText: 'Email or mobile',
              prefixIcon: Icon(Icons.person_outline),
            ),
            validator: (value) => (value == null || value.trim().isEmpty)
                ? 'Enter your email or mobile'
                : null,
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _loginPassword,
            obscureText: _obscureLogin,
            autofillHints: const [AutofillHints.password],
            onFieldSubmitted: (_) => _busy ? null : _submitLogin(),
            decoration: InputDecoration(
              labelText: 'Password',
              prefixIcon: const Icon(Icons.lock_outline),
              suffixIcon: IconButton(
                onPressed: () => setState(() => _obscureLogin = !_obscureLogin),
                icon: Icon(
                  _obscureLogin
                      ? Icons.visibility_outlined
                      : Icons.visibility_off_outlined,
                ),
              ),
            ),
            validator: (value) =>
                (value == null || value.isEmpty) ? 'Enter your password' : null,
          ),
          const SizedBox(height: 14),
          _captchaButton(),
          const SizedBox(height: 14),
          FilledButton(
            onPressed: _busy ? null : _submitLogin,
            child: _busy
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.2,
                      color: Colors.white,
                    ),
                  )
                : const Text('Continue securely'),
          ),
          const SizedBox(height: 6),
          TextButton(
            onPressed: _busy
                ? null
                : () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => const ForgotPasswordScreen(),
                    ),
                  ),
            child: const Text('Forgot password?'),
          ),
          const SizedBox(height: 4),
          Text(
            'Sign-in is protected by a mandatory two-factor challenge. Keep your authenticator app or recovery codes ready.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 11, color: AppColors.muted, height: 1.4),
          ),
        ],
      ),
    );
  }

  Widget _buildRegister() {
    return Form(
      key: _registerForm,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _modeTabs(),
          const SizedBox(height: 18),
          _errorBanner(),
          TextFormField(
            controller: _fullName,
            textCapitalization: TextCapitalization.words,
            textInputAction: TextInputAction.next,
            decoration: const InputDecoration(
              labelText: 'Full name',
              prefixIcon: Icon(Icons.badge_outlined),
            ),
            validator: (value) => (value == null || value.trim().length < 2)
                ? 'Enter your full name'
                : null,
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _email,
            keyboardType: TextInputType.emailAddress,
            textInputAction: TextInputAction.next,
            decoration: const InputDecoration(
              labelText: 'Email address',
              prefixIcon: Icon(Icons.mail_outline),
            ),
            validator: (value) {
              final text = (value ?? '').trim();
              if (text.isEmpty) return 'Enter your email address';
              final ok = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(text);
              return ok ? null : 'Enter a valid email address';
            },
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _phone,
            keyboardType: TextInputType.phone,
            textInputAction: TextInputAction.next,
            decoration: const InputDecoration(
              labelText: 'Mobile number (optional)',
              prefixIcon: Icon(Icons.phone_outlined),
            ),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _registerPassword,
            obscureText: _obscureRegister,
            textInputAction: TextInputAction.next,
            decoration: InputDecoration(
              labelText: 'Password',
              prefixIcon: const Icon(Icons.lock_outline),
              helperText: '8+ chars with upper, lower, number and symbol',
              suffixIcon: IconButton(
                onPressed: () =>
                    setState(() => _obscureRegister = !_obscureRegister),
                icon: Icon(
                  _obscureRegister
                      ? Icons.visibility_outlined
                      : Icons.visibility_off_outlined,
                ),
              ),
            ),
            validator: (value) =>
                (value == null || value.isEmpty) ? 'Create a password' : null,
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _confirmPassword,
            obscureText: _obscureConfirm,
            decoration: InputDecoration(
              labelText: 'Confirm password',
              prefixIcon: const Icon(Icons.lock_reset_outlined),
              suffixIcon: IconButton(
                onPressed: () =>
                    setState(() => _obscureConfirm = !_obscureConfirm),
                icon: Icon(
                  _obscureConfirm
                      ? Icons.visibility_outlined
                      : Icons.visibility_off_outlined,
                ),
              ),
            ),
            validator: (value) => (value == null || value.isEmpty)
                ? 'Re-enter your password'
                : null,
          ),
          const SizedBox(height: 14),
          _captchaButton(),
          const SizedBox(height: 14),
          FilledButton(
            onPressed: _busy ? null : _submitRegistration,
            child: _busy
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.2,
                      color: Colors.white,
                    ),
                  )
                : const Text('Create account'),
          ),
          const SizedBox(height: 8),
          Text(
            'By creating an account you agree that VIDHIK provides legal information and does not create a lawyer-client relationship.',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 10.5,
              color: AppColors.muted,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildVerifyOtp() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _stepHeader(
          icon: Icons.mark_email_read_outlined,
          title: 'Verify your identity',
          subtitle:
              'Enter the 6-digit code sent to ${_maskedDestination.isEmpty ? _registrationTarget : _maskedDestination}.',
        ),
        const SizedBox(height: 16),
        _errorBanner(),
        TextField(
          controller: _otp,
          keyboardType: TextInputType.number,
          textAlign: TextAlign.center,
          maxLength: 6,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          style: const TextStyle(
            fontSize: 26,
            letterSpacing: 12,
            fontWeight: FontWeight.w700,
          ),
          decoration: const InputDecoration(
            counterText: '',
            hintText: '••••••',
          ),
        ),
        const SizedBox(height: 8),
        FilledButton(
          onPressed: _busy ? null : _verifySignupOtp,
          child: _busy
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2.2,
                    color: Colors.white,
                  ),
                )
              : const Text('Verify code'),
        ),
        const SizedBox(height: 12),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            TextButton(
              onPressed: _resendSeconds > 0 || _busy ? null : _resendOtp,
              child: Text(
                _resendSeconds > 0
                    ? 'Resend in ${_resendSeconds}s'
                    : 'Resend code',
              ),
            ),
            TextButton(
              onPressed: _busy ? null : () => _switchStep(_AuthStep.register),
              child: const Text('Change details'),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          'Codes expire after 10 minutes. Never share this code with anyone.',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 11, color: AppColors.muted),
        ),
      ],
    );
  }

  Widget _buildSetup2fa() {
    final enrollment = _enrollment;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _stepHeader(
          icon: Icons.security,
          title: 'Set up two-factor authentication',
          subtitle: '2FA is mandatory. Scan the QR code with Google Authenticator, Authy or Microsoft Authenticator.',
        ),
        const SizedBox(height: 16),
        _errorBanner(),
        if (enrollment != null)
          Center(
            child: Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppColors.border),
              ),
              child: _qrImage(enrollment.qrCodeDataUrl),
            ),
          ),
        const SizedBox(height: 12),
        if (enrollment != null && enrollment.totpSecret.isNotEmpty)
          AppCard(
            color: AppColors.background,
            child: Column(
              children: [
                const Text(
                  'Or enter this setup key manually',
                  style: TextStyle(fontSize: 11.5, color: AppColors.muted),
                ),
                const SizedBox(height: 6),
                SelectableText(
                  enrollment.totpSecret,
                  style: const TextStyle(
                    fontFamily: 'monospace',
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.6,
                  ),
                ),
                const SizedBox(height: 6),
                TextButton.icon(
                  onPressed: () {
                    Clipboard.setData(
                      ClipboardData(text: enrollment.totpSecret),
                    );
                    showInfoSnack(context, 'Setup key copied.');
                  },
                  icon: const Icon(Icons.copy, size: 16),
                  label: const Text('Copy key'),
                ),
              ],
            ),
          ),
        const SizedBox(height: 14),
        TextField(
          controller: _totp,
          keyboardType: TextInputType.number,
          textAlign: TextAlign.center,
          maxLength: 6,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          style: const TextStyle(
            fontSize: 24,
            letterSpacing: 10,
            fontWeight: FontWeight.w700,
          ),
          decoration: const InputDecoration(
            counterText: '',
            labelText: '6-digit authenticator code',
          ),
        ),
        const SizedBox(height: 6),
        FilledButton(
          onPressed: _busy ? null : _completeTwoFactorSetup,
          child: _busy
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2.2,
                    color: Colors.white,
                  ),
                )
              : const Text('Activate 2FA and continue'),
        ),
        const SizedBox(height: 8),
        const Text(
          'Two-factor authentication protects your legal matters, documents and conversations.',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 11, color: AppColors.muted, height: 1.4),
        ),
      ],
    );
  }

  Widget _qrImage(String dataUrl) {
    try {
      final raw = dataUrl.contains(',') ? dataUrl.split(',').last : dataUrl;
      final bytes = base64Decode(raw);
      return Image.memory(bytes, width: 190, height: 190, fit: BoxFit.contain);
    } catch (_) {
      return const Padding(
        padding: EdgeInsets.all(16),
        child: Text('QR code unavailable. Use the setup key below.'),
      );
    }
  }

  Widget _buildRecoveryCodes() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _stepHeader(
          icon: Icons.key,
          title: 'Save your recovery codes',
          subtitle: 'Each code can be used once if you lose access to your authenticator app.',
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: AppColors.background,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.border),
          ),
          child: _recoveryCodes.isEmpty
              ? const Text('Recovery codes were not returned by the server.')
              : Wrap(
                  spacing: 12,
                  runSpacing: 8,
                  children: [
                    for (final code in _recoveryCodes)
                      Text(
                        code,
                        style: const TextStyle(
                          fontFamily: 'monospace',
                          fontSize: 12.5,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                  ],
                ),
        ),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: _recoveryCodes.isEmpty
              ? null
              : () {
                  Clipboard.setData(
                    ClipboardData(text: _recoveryCodes.join('\n')),
                  );
                  showInfoSnack(
                    context,
                    'Recovery codes copied. Store them securely.',
                  );
                },
          icon: const Icon(Icons.copy_all_outlined, size: 18),
          label: const Text('Copy all codes'),
        ),
        const SizedBox(height: 14),
        FilledButton(
          onPressed: () {
            // The auth provider is already signed in; the root gate swaps in
            // the workspace automatically.
          },
          child: const Text('Enter VIDHIK'),
        ),
        const SizedBox(height: 8),
        const Text(
          'Do not share these codes. VIDHIK staff will never ask for them.',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 11, color: AppColors.muted),
        ),
      ],
    );
  }

  Widget _buildLoginTwoFactor() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _stepHeader(
          icon: Icons.verified_user_outlined,
          title: _useRecoveryCode
              ? 'Use a recovery code'
              : 'Two-factor verification',
          subtitle: _useRecoveryCode
              ? 'Enter one of the single-use recovery codes you saved during setup.'
              : 'Enter the current 6-digit code from your authenticator app.',
        ),
        const SizedBox(height: 16),
        _errorBanner(),
        TextField(
          controller: _totp,
          keyboardType: _useRecoveryCode
              ? TextInputType.text
              : TextInputType.number,
          textAlign: TextAlign.center,
          maxLength: _useRecoveryCode ? 20 : 6,
          inputFormatters: _useRecoveryCode
              ? null
              : [FilteringTextInputFormatter.digitsOnly],
          style: TextStyle(
            fontSize: _useRecoveryCode ? 18 : 26,
            letterSpacing: _useRecoveryCode ? 2 : 10,
            fontWeight: FontWeight.w700,
          ),
          decoration: const InputDecoration(counterText: ''),
        ),
        const SizedBox(height: 6),
        FilledButton(
          onPressed: _busy ? null : _submitLoginTwoFactor,
          child: _busy
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2.2,
                    color: Colors.white,
                  ),
                )
              : const Text('Verify and sign in'),
        ),
        const SizedBox(height: 8),
        TextButton(
          onPressed: _busy
              ? null
              : () => setState(() {
                  _useRecoveryCode = !_useRecoveryCode;
                  _totp.clear();
                  _error = null;
                }),
          child: Text(
            _useRecoveryCode
                ? 'Use authenticator app instead'
                : 'Use a recovery code',
          ),
        ),
        TextButton(
          onPressed: _busy
              ? null
              : () {
                  setState(() {
                    _pendingTwoFactorToken = null;
                    _step = _AuthStep.login;
                    _error = null;
                  });
                },
          child: const Text('Back to sign in'),
        ),
      ],
    );
  }

  Widget _stepHeader({
    required IconData icon,
    required String title,
    required String subtitle,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, color: AppColors.teal, size: 22),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                title,
                style: const TextStyle(
                  fontSize: 16.5,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Text(
          subtitle,
          style: const TextStyle(
            fontSize: 12.5,
            color: AppColors.muted,
            height: 1.4,
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Password reset
// ---------------------------------------------------------------------------

class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _email = TextEditingController();
  final _otp = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();

  bool _requested = false;
  bool _busy = false;
  String? _error;
  String? _info;

  bool _captchaEnabled = false;
  String _siteKey = '';
  String? _captchaToken;

  @override
  void initState() {
    super.initState();
    _loadCaptchaConfig();
  }

  @override
  void dispose() {
    _email.dispose();
    _otp.dispose();
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _loadCaptchaConfig() async {
    try {
      final config = await context.read<ApiService>().turnstileConfig();
      if (!mounted) return;
      setState(() {
        _siteKey = '${config['site_key'] ?? ''}';
        _captchaEnabled = config['enabled'] == true && _siteKey.isNotEmpty;
      });
    } catch (_) {
      // The request step will surface a server error if CAPTCHA is mandatory.
    }
  }

  Future<String?> _captcha() async {
    if (!_captchaEnabled) return null;
    if (_captchaToken != null) return _captchaToken;
    final baseUrl = context.read<SettingsProvider>().baseUrl;
    final token = await TurnstileDialog.show(
      context,
      siteKey: _siteKey,
      baseUrl: baseUrl,
    );
    if (token != null) {
      setState(() {
        _captchaToken = token;
      });
    }
    return token;
  }

  Future<void> _requestReset() async {
    final email = _email.text.trim();
    if (!RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(email)) {
      setState(() {
        _error = 'Enter the email registered with VIDHIK.';
      });
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final token = await _captcha();
      if (_captchaEnabled && token == null) {
        throw const ApiException('Complete the security verification first.');
      }
      final response = await context.read<ApiService>().forgotPassword(
        email: email,
        turnstileToken: token,
      );
      if (!mounted) return;
      setState(() {
        _requested = true;
        _info =
            '${response['message'] ?? 'If the email is registered, a reset code has been sent.'}';
        _captchaToken = null;
      });
    } on ApiException catch (e) {
      setState(() {
        _error = e.message;
        _captchaToken = null;
      });
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  Future<void> _resetPassword() async {
    if (_otp.text.trim().length != 6) {
      setState(() {
        _error = 'Enter the 6-digit reset code.';
      });
      return;
    }
    if (_password.text.length < 8 ||
        !RegExp(r'[A-Z]').hasMatch(_password.text) ||
        !RegExp(r'[a-z]').hasMatch(_password.text) ||
        !RegExp(r'[0-9]').hasMatch(_password.text) ||
        !RegExp(r'[^A-Za-z0-9]').hasMatch(_password.text)) {
      setState(
        () => _error = 'New password must be 8+ characters with upper, lower, number and symbol.',
      );
      return;
    }
    if (_password.text != _confirm.text) {
      setState(() {
        _error = 'Passwords do not match.';
      });
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await context.read<ApiService>().resetPassword(
        email: _email.text.trim(),
        otpCode: _otp.text.trim(),
        newPassword: _password.text,
        confirmPassword: _confirm.text,
      );
      if (!mounted) return;
      showInfoSnack(
        context,
        'Password reset successful. Sign in with your new password.',
      );
      Navigator.of(context).pop();
    } on ApiException catch (e) {
      setState(() {
        _error = e.message;
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
    return Scaffold(
      appBar: AppBar(title: const Text('Reset password')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_error != null)
              Container(
                margin: const EdgeInsets.only(bottom: 14),
                padding: const EdgeInsets.all(11),
                decoration: BoxDecoration(
                  color: AppColors.danger.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  _error!,
                  style: const TextStyle(
                    color: AppColors.danger,
                    fontSize: 12.5,
                  ),
                ),
              ),
            if (_info != null)
              Container(
                margin: const EdgeInsets.only(bottom: 14),
                padding: const EdgeInsets.all(11),
                decoration: BoxDecoration(
                  color: AppColors.success.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  _info!,
                  style: const TextStyle(
                    color: AppColors.success,
                    fontSize: 12.5,
                  ),
                ),
              ),
            TextField(
              controller: _email,
              enabled: !_requested,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(
                labelText: 'Registered email',
                prefixIcon: Icon(Icons.mail_outline),
              ),
            ),
            const SizedBox(height: 12),
            if (!_requested)
              FilledButton(
                onPressed: _busy ? null : _requestReset,
                child: _busy
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2.2,
                          color: Colors.white,
                        ),
                      )
                    : const Text('Send reset code'),
              )
            else ...[
              TextField(
                controller: _otp,
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                maxLength: 6,
                decoration: const InputDecoration(
                  labelText: '6-digit reset code',
                  counterText: '',
                  prefixIcon: Icon(Icons.pin_outlined),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _password,
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'New password',
                  prefixIcon: Icon(Icons.lock_outline),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _confirm,
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'Confirm new password',
                  prefixIcon: Icon(Icons.lock_reset_outlined),
                ),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: _busy ? null : _resetPassword,
                child: _busy
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2.2,
                          color: Colors.white,
                        ),
                      )
                    : const Text('Reset password'),
              ),
              TextButton(
                onPressed: _busy ? null : _requestReset,
                child: const Text('Resend reset code'),
              ),
            ],
            const SizedBox(height: 18),
            const Text(
              'Password resets revoke all active sessions. You will need to sign in again on every device.',
              style: TextStyle(
                fontSize: 11.5,
                color: AppColors.muted,
                height: 1.4,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
