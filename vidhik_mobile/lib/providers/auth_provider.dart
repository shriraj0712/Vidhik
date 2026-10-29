import 'package:flutter/foundation.dart';

import '../core/network/api_client.dart';
import '../core/storage/token_store.dart';
import '../models/auth_user.dart';
import '../services/api_service.dart';

enum AuthStatus { booting, signedOut, signedIn }

class AuthProvider extends ChangeNotifier {
  AuthProvider({required this.api, required this.client, required this.store}) {
    client.onUnauthorized = _onUnauthorized;
  }

  final ApiService api;
  final ApiClient client;
  final TokenStore store;

  AuthStatus _status = AuthStatus.booting;
  AuthUser? _user;
  String? _token;
  String? _sessionNotice;

  AuthStatus get status => _status;
  AuthUser? get user => _user;
  String? get token => _token;
  String? get sessionNotice => _sessionNotice;
  bool get isSignedIn => _status == AuthStatus.signedIn && _token != null;
  bool get isLawyer => _user?.isLawyer ?? false;
  bool get isAdmin => _user?.isAdmin ?? false;

  void clearSessionNotice() {
    _sessionNotice = null;
  }

  Future<void> bootstrap() async {
    final saved = await store.readToken();
    if (saved == null || saved.isEmpty) {
      _status = AuthStatus.signedOut;
      notifyListeners();
      return;
    }
    _token = saved;
    client.token = saved;
    try {
      _user = await api.me();
      _status = AuthStatus.signedIn;
    } catch (_) {
      _token = null;
      _user = null;
      client.token = null;
      await store.clear();
      _status = AuthStatus.signedOut;
    }
    notifyListeners();
  }

  Future<AuthChallenge> login({
    required String identifier,
    required String password,
    String? turnstileToken,
  }) {
    return api.login(
      identifier: identifier,
      password: password,
      turnstileToken: turnstileToken,
    );
  }

  Future<AuthSession> verifyLogin({
    required String twoFactorToken,
    required String code,
    bool useRecoveryCode = false,
  }) async {
    final session = await api.verifyTwoFactorLogin(
      twoFactorToken: twoFactorToken,
      code: code,
      useRecoveryCode: useRecoveryCode,
    );
    await _establishSession(session);
    return session;
  }

  Future<RegistrationInitiation> registerInitiate({
    required String fullName,
    required String email,
    required String password,
    String? confirmPassword,
    String? phone,
    String? turnstileToken,
  }) {
    return api.registerInitiate(
      fullName: fullName,
      email: email,
      password: password,
      confirmPassword: confirmPassword,
      phone: phone,
      turnstileToken: turnstileToken,
    );
  }

  Future<TwoFactorEnrollment> verifySignupOtp({
    required String target,
    required String otpCode,
  }) {
    return api.verifyOtp(target: target, otpCode: otpCode);
  }

  Future<AuthSession> completeTwoFactorSetup({
    required String setupToken,
    required String totpCode,
  }) async {
    final session = await api.completeTwoFactorSetup(
      setupToken: setupToken,
      totpCode: totpCode,
    );
    await _establishSession(session);
    return session;
  }

  Future<void> _establishSession(AuthSession session) async {
    if (session.token.isEmpty) {
      throw const ApiException('The server did not return a session token.');
    }
    _token = session.token;
    client.token = session.token;
    await store.writeToken(session.token);
    _user = session.user;
    _status = AuthStatus.signedIn;
    _sessionNotice = null;
    notifyListeners();
  }

  Future<void> refreshProfile() async {
    if (_token == null) return;
    try {
      _user = await api.me();
      notifyListeners();
    } on ApiException catch (e) {
      if (e.isUnauthorized) {
        await _clearLocalSession();
      }
    }
  }

  void updateCachedUser(AuthUser user) {
    _user = user;
    notifyListeners();
  }

  Future<void> logout() async {
    try {
      await api.logout();
    } catch (_) {
      // Local sign-out must succeed even when the backend is unreachable.
    }
    await _clearLocalSession();
  }

  Future<void> _clearLocalSession() async {
    _token = null;
    _user = null;
    client.token = null;
    await store.clear();
    _status = AuthStatus.signedOut;
    notifyListeners();
  }

  void _onUnauthorized() {
    if (_status == AuthStatus.signedIn) {
      _sessionNotice = 'Your session expired. Please sign in again.';
    }
    _token = null;
    _user = null;
    store.clear();
    _status = AuthStatus.signedOut;
    notifyListeners();
  }
}
