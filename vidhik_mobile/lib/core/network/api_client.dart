import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

/// A user-presentable API failure.
class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final dynamic data;

  const ApiException(this.message, {this.statusCode, this.data});

  bool get isUnauthorized => statusCode == 401;

  @override
  String toString() => message;
}

class DownloadResult {
  final List<int> bytes;
  final String filename;
  final String contentType;

  const DownloadResult({
    required this.bytes,
    required this.filename,
    required this.contentType,
  });
}

/// Centralized HTTP client for the existing VIDHIK FastAPI backend.
///
/// Responsibilities: configurable base URL, bearer-token handling, JSON
/// encode/decode, multipart uploads, binary downloads, timeouts, structured
/// errors and 401 propagation. Credentials are never logged.
class ApiClient {
  ApiClient({required this.tokenStore});

  final dynamic tokenStore;
  http.Client _client = http.Client();

  String _baseUrl = '';
  String? _token;

  /// Invoked once when the backend rejects the session.
  void Function()? onUnauthorized;

  static const Duration defaultTimeout = Duration(seconds: 40);
  static const Duration chatTimeout = Duration(seconds: 120);
  static const Duration uploadTimeout = Duration(seconds: 300);

  String get baseUrl => _baseUrl;
  set baseUrl(String value) {
    _baseUrl = value.trim().replaceAll(RegExp(r'/+$'), '');
  }

  String? get token => _token;
  set token(String? value) => _token = value;

  void close() => _client.close();

  Uri _uri(String path, [Map<String, dynamic>? query]) {
    assert(_baseUrl.isNotEmpty, 'ApiClient.baseUrl must be configured');
    final normalizedPath = path.startsWith('/') ? path : '/$path';
    final uri = Uri.parse('$_baseUrl$normalizedPath');
    if (query == null || query.isEmpty) return uri;
    final params = <String, String>{};
    query.forEach((key, value) {
      if (value == null) return;
      if (value is Iterable) {
        final list = value.map((e) => '$e').where((e) => e.isNotEmpty).toList();
        if (list.isNotEmpty) params[key] = list.join(',');
      } else {
        final text = '$value';
        if (text.isNotEmpty) params[key] = text;
      }
    });
    if (params.isEmpty) return uri;
    return uri.replace(queryParameters: {...uri.queryParameters, ...params});
  }

  Map<String, String> _headers({bool json = true, Map<String, String>? extra}) {
    final headers = <String, String>{'Accept': 'application/json'};
    if (json) headers['Content-Type'] = 'application/json';
    if (_token != null && _token!.isNotEmpty) {
      headers['Authorization'] = 'Bearer $_token';
    }
    if (extra != null) headers.addAll(extra);
    return headers;
  }

  Future<dynamic> get(
    String path, {
    Map<String, dynamic>? query,
    Duration? timeout,
  }) {
    return _send('GET', path, query: query, timeout: timeout);
  }

  Future<dynamic> post(
    String path, {
    Object? body,
    Map<String, dynamic>? query,
    Duration? timeout,
  }) {
    return _send('POST', path, body: body, query: query, timeout: timeout);
  }

  Future<dynamic> put(String path, {Object? body, Duration? timeout}) {
    return _send('PUT', path, body: body, timeout: timeout);
  }

  Future<dynamic> patch(String path, {Object? body, Duration? timeout}) {
    return _send('PATCH', path, body: body, timeout: timeout);
  }

  Future<dynamic> delete(String path, {Object? body, Duration? timeout}) {
    return _send('DELETE', path, body: body, timeout: timeout);
  }

  Future<dynamic> _send(
    String method,
    String path, {
    Object? body,
    Map<String, dynamic>? query,
    Duration? timeout,
  }) async {
    final uri = _uri(path, query);
    final request = http.Request(method, uri); // ignore: deprecated_member_use
    request.headers.addAll(_headers(json: body != null));
    request.headers['Content-Type'] =
        'application/json'; // GETs tolerate this on FastAPI
    if (body != null) {
      request.body = jsonEncode(body);
    }

    final effectiveTimeout = timeout ?? defaultTimeout;
    try {
      final streamed = await _client.send(request).timeout(effectiveTimeout);
      final response = await http.Response.fromStream(streamed)
          .timeout(effectiveTimeout);
      return _decode(response);
    } on TimeoutException {
      throw const ApiException(
        'The server took too long to respond. Check your connection and try again.',
      );
    } on SocketException {
      throw const ApiException(
        'Unable to reach the VIDHIK server. Check the backend URL in Settings and your network connection.',
      );
    } on http.ClientException {
      throw const ApiException(
        'Unable to reach the VIDHIK server. Check the backend URL in Settings and your network connection.',
      );
    }
  }

  Future<dynamic> upload(
    String path, {
    required String filePath,
    String field = 'file',
    Map<String, String> fields = const {},
    Duration? timeout,
  }) async {
    final uri = _uri(path);
    final request = http.MultipartRequest('POST', uri);
    request.headers.addAll(_headers(json: false));
    request.fields.addAll(fields);
    request.files.add(await http.MultipartFile.fromPath(field, filePath));

    try {
      final streamed = await _client
          .send(request)
          .timeout(timeout ?? uploadTimeout);
      final response = await http.Response.fromStream(streamed)
          .timeout(timeout ?? uploadTimeout);
      return _decode(response);
    } on TimeoutException {
      throw const ApiException(
        'The upload timed out. Try a smaller file or a faster connection.',
      );
    } on SocketException {
      throw const ApiException(
        'Unable to reach the VIDHIK server while uploading. Check your connection.',
      );
    }
  }

  Future<DownloadResult> postDownload(
    String path, {
    Object? body,
    String fallbackName = 'export',
  }) async {
    final uri = _uri(path);
    final request = http.Request('POST', uri); // ignore: deprecated_member_use
    request.headers.addAll(_headers());
    if (body != null) request.body = jsonEncode(body);
    try {
      final streamed = await _client.send(request).timeout(uploadTimeout);
      final response = await http.Response.fromStream(streamed);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        _decode(response);
      }
      final disposition = response.headers['content-disposition'] ?? '';
      var filename = fallbackName;
      final match = RegExp(r'filename="?([^";]+)"?').firstMatch(disposition);
      if (match != null) filename = match.group(1)!.trim();
      return DownloadResult(
        bytes: response.bodyBytes,
        filename: filename,
        contentType:
            response.headers['content-type'] ?? 'application/octet-stream',
      );
    } on TimeoutException {
      throw const ApiException('The export timed out. Please try again.');
    } on SocketException {
      throw const ApiException('Unable to reach the server for this export.');
    }
  }

  Future<DownloadResult> download(
    String path, {
    String fallbackName = 'export',
  }) async {
    final uri = _uri(path);
    final request = http.Request('GET', uri); // ignore: deprecated_member_use
    request.headers.addAll(_headers(json: false));
    try {
      final streamed = await _client.send(request).timeout(uploadTimeout);
      final response = await http.Response.fromStream(streamed);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        _decode(response);
      }
      final disposition = response.headers['content-disposition'] ?? '';
      var filename = fallbackName;
      final match = RegExp(r'filename="?([^";]+)"?').firstMatch(disposition);
      if (match != null) filename = match.group(1)!.trim();
      return DownloadResult(
        bytes: response.bodyBytes,
        filename: filename,
        contentType:
            response.headers['content-type'] ?? 'application/octet-stream',
      );
    } on TimeoutException {
      throw const ApiException('The download timed out. Please try again.');
    } on SocketException {
      throw const ApiException('Unable to reach the server for this download.');
    }
  }

  dynamic _decode(http.Response response) {
    final contentType = response.headers['content-type'] ?? '';
    dynamic data;
    if (contentType.contains('application/json')) {
      try {
        data = jsonDecode(utf8.decode(response.bodyBytes));
      } catch (_) {
        data = <String, dynamic>{'detail': 'Invalid JSON response from server'};
      }
    } else {
      final text = utf8.decode(response.bodyBytes, allowMalformed: true);
      data = <String, dynamic>{'detail': text};
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return data;
    }

    final message = _extractMessage(data, response.statusCode);
    if (response.statusCode == 401) {
      onUnauthorized?.call();
    }
    throw ApiException(message, statusCode: response.statusCode, data: data);
  }

  String _extractMessage(dynamic data, int statusCode) {
    if (data is Map) {
      final detail = data['detail'];
      if (detail is String && detail.trim().isNotEmpty) return detail;
      if (detail is List) {
        final parts = detail
            .map((item) {
              if (item is Map) {
                final loc = item['loc'];
                final field = loc is List && loc.isNotEmpty
                    ? '${loc.last}: '
                    : '';
                final msg = item['msg'] ?? 'Invalid value';
                return '$field$msg';
              }
              return '$item';
            })
            .where((e) => e.isNotEmpty)
            .toList();
        if (parts.isNotEmpty) return parts.join('\n');
      }
      final msg = data['message'];
      if (msg is String && msg.isNotEmpty) return msg;
      final error = data['error'];
      if (error is String && error.isNotEmpty) return error;
    }
    if (data is String && data.trim().isNotEmpty && data.length < 500) {
      return data;
    }
    if (statusCode == 401) {
      return 'Your session has expired. Please sign in again.';
    }
    if (statusCode == 403) {
      return 'You do not have permission to perform this action.';
    }
    if (statusCode == 404) return 'The requested resource was not found.';
    if (statusCode == 429) {
      return 'Too many requests. Please wait a moment and retry.';
    }
    if (statusCode >= 500) {
      return 'The VIDHIK server encountered an error. Please try again shortly.';
    }
    return 'Request failed (HTTP $statusCode).';
  }
}
