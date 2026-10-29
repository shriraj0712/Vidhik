import 'package:flutter/foundation.dart';

import '../core/network/api_client.dart';
import '../models/chat.dart';
import '../services/api_service.dart';

/// Conversation state for the grounded VIDHIK legal assistant.
///
/// History is sent to the backend on every turn so follow-up questions keep
/// context. No answer is ever synthesized locally: when the backend is
/// unavailable the UI shows that failure explicitly.
class ChatProvider extends ChangeNotifier {
  ChatProvider({required this.api});

  final ApiService api;

  final List<ChatTurn> _turns = [];
  String? _conversationId;
  String _language = 'en';
  bool _sending = false;
  String? _error;

  List<ChatTurn> get turns => List.unmodifiable(_turns);
  String? get conversationId => _conversationId;
  String get language => _language;
  bool get sending => _sending;
  String? get error => _error;
  bool get isEmpty => _turns.isEmpty;

  void setLanguage(String value) {
    _language = value;
    notifyListeners();
  }

  void clear() {
    _turns.clear();
    _conversationId = null;
    _error = null;
    notifyListeners();
  }

  Future<void> send(String message, {int? evidenceId}) async {
    final text = message.trim();
    if (text.isEmpty || _sending) return;

    _sending = true;
    _error = null;
    _turns.add(ChatTurn(role: 'user', content: text));
    notifyListeners();

    final history = <Map<String, dynamic>>[];
    for (final turn in _turns.take(_turns.length - 1).toList()) {
      history.add({'role': turn.role, 'content': turn.content});
    }
    if (history.length > 20) {
      history.removeRange(0, history.length - 20);
    }

    try {
      final reply = await api.chat(
        message: text,
        conversationId: _conversationId,
        history: history,
        language: _language,
        evidenceId: evidenceId,
      );
      _conversationId = reply.conversationId.isEmpty
          ? _conversationId
          : reply.conversationId;
      _turns.add(
        ChatTurn(
          role: 'assistant',
          content: reply.answer,
          sources: reply.sources,
          provisions: reply.provisions,
          groundingStatus: reply.groundingStatus,
          isGrounded: reply.isGrounded,
          disclaimer: reply.disclaimer,
          conversationId: reply.conversationId,
        ),
      );
    } on ApiException catch (e) {
      _error = e.message;
      _turns.add(
        ChatTurn(
          role: 'assistant',
          content: e.message,
          isError: true,
          groundingStatus: 'error',
        ),
      );
    } catch (e) {
      _error = 'Unable to reach the VIDHIK assistant. Please try again.';
      _turns.add(
        ChatTurn(
          role: 'assistant',
          content: _error!,
          isError: true,
          groundingStatus: 'error',
        ),
      );
    } finally {
      _sending = false;
      notifyListeners();
    }
  }
}
