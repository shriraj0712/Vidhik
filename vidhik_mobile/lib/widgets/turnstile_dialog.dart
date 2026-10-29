import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../core/theme/app_theme.dart';

/// Renders the real Cloudflare Turnstile widget hosted by the VIDHIK backend
/// (`/static/turnstile.html`) and returns the issued token.
///
/// The app never fabricates or reuses a CAPTCHA token: if the widget cannot
/// verify the deployment hostname, the exact error is surfaced and the user
/// can retry. Test site keys issued by Cloudflare pass automatically in
/// development.
class TurnstileDialog extends StatefulWidget {
  const TurnstileDialog({
    super.key,
    required this.siteKey,
    required this.baseUrl,
  });

  final String siteKey;
  final String baseUrl;

  static Future<String?> show(
    BuildContext context, {
    required String siteKey,
    required String baseUrl,
  }) {
    return showDialog<String>(
      context: context,
      barrierDismissible: false,
      builder: (_) => TurnstileDialog(siteKey: siteKey, baseUrl: baseUrl),
    );
  }

  @override
  State<TurnstileDialog> createState() => _TurnstileDialogState();
}

class _TurnstileDialogState extends State<TurnstileDialog> {
  late final WebViewController _controller;
  bool _loading = true;
  String? _error;
  String? _token;

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(Colors.white)
      ..addJavaScriptChannel(
        'TurnstileBridge',
        onMessageReceived: _onBridgeMessage,
      )
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageFinished: (_) {
            if (mounted) {
              setState(() {
                _loading = false;
              });
            }
          },
          onWebResourceError: (error) {
            if (!mounted) return;
            setState(() {
              _loading = false;
              _error =
                  'Could not load the verification widget: ${error.description}';
            });
          },
        ),
      );
    _load();
  }

  void _load() {
    final uri = Uri.parse('${widget.baseUrl}/static/turnstile.html')
        .replace(queryParameters: {'sitekey': widget.siteKey});
    setState(() {
      _loading = true;
      _error = null;
    });
    _controller.loadRequest(uri);
  }

  void _onBridgeMessage(JavaScriptMessage message) {
    try {
      final data = jsonDecode(message.message);
      if (data is! Map) return;
      final type = data['type'];
      if (type == 'token') {
        final token = '${data['token'] ?? ''}';
        if (token.isNotEmpty) {
          setState(() {
            _token = token;
          });
          Navigator.of(context).pop(token);
        }
      } else if (type == 'error') {
        setState(() {
          _error = '${data['message'] ?? 'Verification failed. Please retry.'}';
        });
      }
    } catch (_) {
      // Ignore malformed bridge messages.
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 40),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(18, 16, 18, 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.verified_user_outlined, color: AppColors.teal),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text(
                    'Security verification',
                    style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.close),
                  tooltip: 'Close',
                ),
              ],
            ),
            const Text(
              'Complete the Cloudflare challenge to confirm you are a person, not an automated script.',
              style: TextStyle(
                fontSize: 12.5,
                color: AppColors.muted,
                height: 1.4,
              ),
            ),
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Container(
                height: 300,
                color: Colors.white,
                child: Stack(
                  children: [
                    WebViewWidget(controller: _controller),
                    if (_loading)
                      const Center(
                        child: CircularProgressIndicator(strokeWidth: 2.4),
                      ),
                  ],
                ),
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppColors.danger.withValues(alpha: 0.07),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  _error!,
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.danger,
                    height: 1.4,
                  ),
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                'If the widget reports a domain error, the backend hostname must be allowed for this '
                'Turnstile site key in the Cloudflare dashboard. For local development, use Cloudflare '
                'test keys on both the site key and secret key.',
                style: TextStyle(
                  fontSize: 11.5,
                  color: AppColors.muted,
                  height: 1.4,
                ),
              ),
            ],
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _load,
                    icon: const Icon(Icons.refresh, size: 18),
                    label: const Text('Reload'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: FilledButton(
                    onPressed: _token == null
                        ? null
                        : () => Navigator.of(context).pop(_token),
                    child: const Text('Continue'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
