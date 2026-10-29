import 'package:flutter_test/flutter_test.dart';
import 'package:vidhik_mobile/core/utils/format.dart';
import 'package:vidhik_mobile/models/auth_user.dart';
import 'package:vidhik_mobile/models/legal.dart';

/// Contract tests for the defensive parsing layer. The VIDHIK backend returns
/// nullable and mixed-shape payloads, so these helpers are the single place
/// where malformed values are absorbed.
void main() {
  group('format helpers', () {
    test('firstNonEmpty skips null, empty and literal null strings', () {
      expect(firstNonEmpty([null, '', 'null', 'Fallback']), 'Fallback');
      expect(firstNonEmpty([], 'default'), 'default');
    });

    test('asInt tolerates numeric strings and null', () {
      expect(asInt('12'), 12);
      expect(asInt(4.9), 4);
      expect(asInt(null, 7), 7);
    });

    test('asMapList drops non-map entries', () {
      final result = asMapList([
        {'id': 1},
        'ignored',
        null,
      ]);
      expect(result, hasLength(1));
      expect(result.first['id'], 1);
    });

    test('cleanLegalText collapses statutory whitespace', () {
      expect(
        cleanLegalText('  Section   5  \n\n\n  text '),
        'Section 5\n\ntext',
      );
    });

    test('initialsOf handles single and multiple names', () {
      expect(initialsOf('Asha Rao'), 'AR');
      expect(initialsOf('Vidhik'), 'V');
      expect(initialsOf('   '), 'V');
    });

    test('formatDate renders ISO timestamps and tolerates junk', () {
      expect(formatDate('2026-10-19T10:00:00Z'), contains('2026'));
      expect(formatDate('not-a-date'), '—');
    });
  });

  group('AuthUser parsing', () {
    test('reads the session payload returned by /api/auth/me', () {
      final user = AuthUser.fromJson({
        'user_id': 42,
        'username': 'asha',
        'email': 'asha@example.com',
        'full_name': 'Asha Rao',
        'role': 'lawyer',
        'lawyer_id': 9,
        'two_factor_enabled': true,
      });
      expect(user.userId, 42);
      expect(user.isLawyer, isTrue);
      expect(user.isAdmin, isFalse);
      expect(user.displayRole, 'Advocate');
      expect(user.lawyerId, 9);
      expect(user.safeName, 'Asha Rao');
    });

    test('falls back to email when full name is missing', () {
      final user = AuthUser.fromJson({'email': 'citizen@example.com'});
      expect(user.fullName, 'citizen@example.com');
      expect(user.displayRole, 'Citizen');
    });
  });

  group('auth challenge parsing', () {
    test('two-factor challenge exposes the token', () {
      final challenge = AuthChallenge.fromJson({
        'status': '2fa_required',
        'two_factor_token': 'abc',
      });
      expect(challenge.requiresTwoFactor, isTrue);
      expect(challenge.twoFactorToken, 'abc');
    });

    test('registration response maps masked destination', () {
      final initiation = RegistrationInitiation.fromJson({
        'target': 'a***@example.com',
        'destination_masked': 'a***@example.com',
        'expires_in_seconds': 300,
      });
      expect(initiation.target, 'a***@example.com');
      expect(initiation.expiresInSeconds, 300);
    });
  });

  group('legal models', () {
    test('statute section tolerates alternate field names', () {
      final section = StatuteSection.fromJson({
        'section_id': 11,
        'section_number': '5',
        'section_title': 'Duty of care',
        'section_text': 'Text',
        'law_name': 'Bharatiya Nyaya Sanhita, 2023',
      });
      expect(section.sectionNumber, '5');
      expect(section.sectionTitle, 'Duty of care');
      expect(section.text, contains('Text'));
    });
  });
}
