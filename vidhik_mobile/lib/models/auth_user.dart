import '../../core/utils/format.dart';

/// Matches the backend `AuthUserResponse` / session payload.
class AuthUser {
  final int userId;
  final String username;
  final String email;
  final String fullName;
  final String? phone;
  final String role;
  final int? lawyerId;
  final bool isActive;
  final bool emailVerified;
  final bool phoneVerified;
  final bool twoFactorEnabled;
  final String accountStatus;

  const AuthUser({
    required this.userId,
    required this.username,
    required this.email,
    required this.fullName,
    required this.role,
    this.phone,
    this.lawyerId,
    this.isActive = true,
    this.emailVerified = true,
    this.phoneVerified = false,
    this.twoFactorEnabled = true,
    this.accountStatus = 'active',
  });

  bool get isLawyer => role.toLowerCase() == 'lawyer';
  bool get isAdmin => role.toLowerCase() == 'admin';

  String get displayRole {
    switch (role.toLowerCase()) {
      case 'lawyer':
        return 'Advocate';
      case 'admin':
        return 'Administrator';
      default:
        return 'Citizen';
    }
  }

  String get safeName =>
      fullName.trim().isNotEmpty ? fullName.trim() : username;

  factory AuthUser.fromJson(dynamic json) {
    final map = asMap(json);
    final email = asString(map['email']);
    final fullName = firstNonEmpty([map['full_name'], map['name']]);
    return AuthUser(
      userId: asInt(map['user_id']),
      username: firstNonEmpty([
        map['username'],
        email.split('@').first,
        'user',
      ]),
      email: email,
      fullName: fullName.isEmpty ? email : fullName,
      phone: asString(map['phone']).isEmpty ? null : asString(map['phone']),
      role: firstNonEmpty([map['role'], 'user']),
      lawyerId: map['lawyer_id'] == null ? null : asInt(map['lawyer_id']),
      isActive: asBool(map['is_active'], true),
      emailVerified: asBool(map['email_verified'], true),
      phoneVerified: asBool(map['phone_verified']),
      twoFactorEnabled: asBool(map['two_factor_enabled'], true),
      accountStatus: firstNonEmpty([map['account_status'], 'active']),
    );
  }

  AuthUser copyWith({String? fullName, String? phone}) {
    return AuthUser(
      userId: userId,
      username: username,
      email: email,
      fullName: fullName ?? this.fullName,
      phone: phone ?? this.phone,
      role: role,
      lawyerId: lawyerId,
      isActive: isActive,
      emailVerified: emailVerified,
      phoneVerified: phoneVerified,
      twoFactorEnabled: twoFactorEnabled,
      accountStatus: accountStatus,
    );
  }
}

/// Result of the two-step login / signup challenge.
class AuthChallenge {
  final String status;
  final String? twoFactorToken;
  final String? message;

  const AuthChallenge({
    required this.status,
    this.twoFactorToken,
    this.message,
  });

  bool get requiresTwoFactor =>
      twoFactorToken != null && twoFactorToken!.isNotEmpty;

  factory AuthChallenge.fromJson(dynamic json) {
    final map = asMap(json);
    return AuthChallenge(
      status: firstNonEmpty([map['status']]),
      twoFactorToken: firstNonEmpty([
        map['two_factor_token'],
        map['two_factor_setup_token'],
      ]),
      message: asString(map['message']),
    );
  }
}

/// Registration step 1 response.
class RegistrationInitiation {
  final String target;
  final String maskedDestination;
  final int expiresInSeconds;
  final int resendCooldownSeconds;
  final String message;

  const RegistrationInitiation({
    required this.target,
    required this.maskedDestination,
    required this.expiresInSeconds,
    required this.resendCooldownSeconds,
    required this.message,
  });

  factory RegistrationInitiation.fromJson(dynamic json) {
    final map = asMap(json);
    return RegistrationInitiation(
      target: asString(map['target']),
      maskedDestination: asString(map['destination_masked']),
      expiresInSeconds: asInt(map['expires_in_seconds'], 600),
      resendCooldownSeconds: asInt(map['resend_cooldown_seconds'], 60),
      message: asString(map['message']),
    );
  }
}

/// OTP verification response carrying mandatory 2FA enrolment material.
class TwoFactorEnrollment {
  final String setupToken;
  final String qrUri;
  final String qrCodeDataUrl;
  final String totpSecret;
  final String message;

  const TwoFactorEnrollment({
    required this.setupToken,
    required this.qrUri,
    required this.qrCodeDataUrl,
    required this.totpSecret,
    required this.message,
  });

  factory TwoFactorEnrollment.fromJson(dynamic json) {
    final map = asMap(json);
    return TwoFactorEnrollment(
      setupToken: firstNonEmpty([
        map['two_factor_setup_token'],
        map['two_factor_token'],
        map['setup_token'],
      ]),
      qrUri: asString(map['qr_uri']),
      qrCodeDataUrl: asString(map['qr_code_data_url']),
      totpSecret: firstNonEmpty([map['totp_secret'], map['secret']]),
      message: asString(map['message']),
    );
  }
}

/// Authenticated session returned by 2FA verification and setup completion.
class AuthSession {
  final String token;
  final AuthUser user;
  final List<String> recoveryCodes;
  final String message;

  const AuthSession({
    required this.token,
    required this.user,
    this.recoveryCodes = const [],
    this.message = '',
  });

  factory AuthSession.fromJson(dynamic json) {
    final map = asMap(json);
    final userMap = map['user'] is Map ? asMap(map['user']) : map;
    final codes = map['recovery_codes'];
    return AuthSession(
      token: firstNonEmpty([
        map['token'],
        map['access_token'],
        userMap['token'],
      ]),
      user: AuthUser.fromJson(userMap),
      recoveryCodes: codes is List
          ? codes.map((e) => asString(e)).where((e) => e.isNotEmpty).toList()
          : const [],
      message: asString(map['message']),
    );
  }
}
