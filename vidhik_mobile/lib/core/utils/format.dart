import 'package:intl/intl.dart';

/// Tolerant JSON helpers. Public API payloads contain nullable and
/// mixed-type fields (for example both `title` and `case_title`), so models
/// read values defensively instead of throwing on a single missing key.
Map<String, dynamic> asMap(dynamic value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) return Map<String, dynamic>.from(value);
  return <String, dynamic>{};
}

List<Map<String, dynamic>> asMapList(dynamic value) {
  if (value is List) {
    return value
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }
  return const [];
}

String asString(dynamic value, [String fallback = '']) {
  if (value == null) return fallback;
  if (value is String) return value;
  return '$value';
}

String firstNonEmpty(List<dynamic> values, [String fallback = '']) {
  for (final value in values) {
    final text = asString(value).trim();
    if (text.isNotEmpty && text.toLowerCase() != 'null') return text;
  }
  return fallback;
}

int asInt(dynamic value, [int fallback = 0]) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value) ?? fallback;
  return fallback;
}

double asDouble(dynamic value, [double fallback = 0]) {
  if (value is double) return value;
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value) ?? fallback;
  return fallback;
}

bool asBool(dynamic value, [bool fallback = false]) {
  if (value is bool) return value;
  if (value is num) return value != 0;
  if (value is String) {
    final normalized = value.toLowerCase().trim();
    if (normalized == 'true' || normalized == '1' || normalized == 'yes') {
      return true;
    }
    if (normalized == 'false' || normalized == '0' || normalized == 'no') {
      return false;
    }
  }
  return fallback;
}

String asListText(dynamic value, {String separator = ' • '}) {
  if (value is List) {
    return value
        .map(
          (e) => e is Map
              ? firstNonEmpty([e['name'], e['title'], e])
              : asString(e),
        )
        .where((e) => e.trim().isNotEmpty)
        .join(separator);
  }
  return asString(value);
}

DateTime? parseDate(dynamic value) {
  if (value == null) return null;
  if (value is DateTime) return value;
  final text = asString(value).trim();
  if (text.isEmpty || text == 'null') return null;
  return DateTime.tryParse(text)?.toLocal();
}

String formatDate(dynamic value, {String fallback = '—'}) {
  final date = parseDate(value);
  if (date == null) return fallback;
  return DateFormat('d MMM yyyy').format(date);
}

String formatDateTime(dynamic value, {String fallback = '—'}) {
  final date = parseDate(value);
  if (date == null) return fallback;
  return DateFormat('d MMM yyyy, h:mm a').format(date);
}

String currency(num value) {
  final formatter = NumberFormat.currency(
    locale: 'en_IN',
    symbol: '₹',
    decimalDigits: value % 1 == 0 ? 0 : 2,
  );
  return formatter.format(value);
}

String compactNumber(num value) {
  if (value >= 10000000) return '${(value / 10000000).toStringAsFixed(1)}Cr';
  if (value >= 100000) return '${(value / 100000).toStringAsFixed(1)}L';
  if (value >= 1000) return '${(value / 1000).toStringAsFixed(1)}k';
  return '$value';
}

/// The backend returns statutory text with markup-like spacing. Collapse
/// repeated whitespace for a readable mobile rendering.
String cleanLegalText(dynamic value) {
  var text = asString(value);
  text = text.replaceAll('\r\n', '\n').replaceAll('\r', '\n');
  text = text.replaceAll(RegExp(r'[ \t]+'), ' ');
  text = text.replaceAll(RegExp(r' *\n *'), '\n');
  text = text.replaceAll(RegExp(r'\n{3,}'), '\n\n');
  return text.trim();
}

String initialsOf(String name) {
  final parts = name
      .trim()
      .split(RegExp(r'\s+'))
      .where((p) => p.isNotEmpty)
      .toList();
  if (parts.isEmpty) return 'V';
  if (parts.length == 1) return parts.first.substring(0, 1).toUpperCase();
  return (parts.first.substring(0, 1) + parts.last.substring(0, 1))
      .toUpperCase();
}

String maskEmail(String email) {
  if (!email.contains('@')) return email;
  final parts = email.split('@');
  final name = parts.first;
  final visible = name.length <= 2 ? name : name.substring(0, 2);
  return '$visible***@${parts.last}';
}
