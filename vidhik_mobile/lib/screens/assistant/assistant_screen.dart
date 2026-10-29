import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../models/chat.dart';
import '../../providers/chat_provider.dart';
import '../../providers/settings_provider.dart';
import '../../widgets/common.dart';
import '../evidence/evidence_screen.dart';

class AssistantScreen extends StatefulWidget {
  const AssistantScreen({super.key});

  @override
  State<AssistantScreen> createState() => _AssistantScreenState();
}

class _AssistantScreenState extends State<AssistantScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();
  final _focusNode = FocusNode();
  int? _evidenceId;

  static const _suggestions = [
    'What are my rights if police stop me without a warrant?',
    'How do I file an FIR under BNSS 2023?',
    'What is the punishment for online financial fraud?',
    'My landlord refuses to return my security deposit. What can I do?',
    'What documents are required for a consumer complaint?',
  ];

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  Future<void> _send([String? preset]) async {
    final text = (preset ?? _controller.text).trim();
    if (text.isEmpty) return;
    final chat = context.read<ChatProvider>();
    if (chat.sending) return;
    _controller.clear();
    FocusScope.of(context).unfocus();
    await chat.send(text, evidenceId: _evidenceId);
    _scrollToEnd();
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 260),
        curve: Curves.easeOut,
      );
    });
  }

  Future<void> _attachEvidence() async {
    final id = await Navigator.of(context).push<int>(
      MaterialPageRoute(builder: (_) => const EvidenceScreen(selectMode: true)),
    );
    if (id != null && mounted) {
      setState(() {
        _evidenceId = id;
      });
      showInfoSnack(
        context,
        'Video evidence #$id attached to your next question.',
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final chat = context.watch<ChatProvider>();
    final settings = context.watch<SettingsProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Vidhik AI Assistant'),
            Text(
              'Grounded in Indian statutory law',
              style: TextStyle(
                fontSize: 10.5,
                fontWeight: FontWeight.w400,
                color: Colors.white70,
              ),
            ),
          ],
        ),
        actions: [
          PopupMenuButton<String>(
            tooltip: 'Response language',
            initialValue: chat.language,
            onSelected: (value) {
              chat.setLanguage(value);
              settings.setLanguage(value);
            },
            itemBuilder: (context) => [
              for (final entry in SettingsProvider.languageNames.entries)
                PopupMenuItem(value: entry.key, child: Text(entry.value)),
            ],
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Row(
                children: [
                  const Icon(Icons.translate, size: 18, color: Colors.white),
                  const SizedBox(width: 4),
                  Text(
                    chat.language.toUpperCase(),
                    style: const TextStyle(color: Colors.white, fontSize: 12),
                  ),
                ],
              ),
            ),
          ),
          IconButton(
            tooltip: 'New conversation',
            onPressed: chat.sending
                ? null
                : () async {
                    final ok = await confirmDialog(
                      context,
                      title: 'Start a new conversation?',
                      message: 'The current conversation stays private but will be cleared from this screen.',
                      confirmLabel: 'New chat',
                    );
                    if (ok) chat.clear();
                  },
            icon: const Icon(Icons.add_comment_outlined),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: chat.isEmpty
                ? _welcome(context)
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.fromLTRB(14, 16, 14, 16),
                    itemCount: chat.turns.length + (chat.sending ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (index >= chat.turns.length) {
                        return const _TypingBubble();
                      }
                      return _TurnBubble(turn: chat.turns[index]);
                    },
                  ),
          ),
          if (_evidenceId != null)
            Container(
              margin: const EdgeInsets.fromLTRB(14, 0, 14, 6),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: AppColors.teal.withValues(alpha: 0.09),
                borderRadius: BorderRadius.circular(9),
              ),
              child: Row(
                children: [
                  const Icon(Icons.videocam, size: 16, color: AppColors.teal),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'Video evidence #$_evidenceId attached',
                      style: const TextStyle(
                        fontSize: 11.5,
                        color: AppColors.teal,
                      ),
                    ),
                  ),
                  InkWell(
                    onTap: () => setState(() => _evidenceId = null),
                    child: const Icon(
                      Icons.close,
                      size: 16,
                      color: AppColors.teal,
                    ),
                  ),
                ],
              ),
            ),
          SafeArea(
            top: false,
            child: Container(
              padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surface,
                border: Border(
                  top: BorderSide(color: Theme.of(context).dividerColor),
                ),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  IconButton(
                    tooltip: 'Attach video evidence',
                    onPressed: chat.sending ? null : _attachEvidence,
                    icon: Icon(
                      Icons.videocam_outlined,
                      color: _evidenceId == null
                          ? AppColors.muted
                          : AppColors.teal,
                    ),
                  ),
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      focusNode: _focusNode,
                      minLines: 1,
                      maxLines: 5,
                      textCapitalization: TextCapitalization.sentences,
                      onSubmitted: (_) => _send(),
                      decoration: InputDecoration(
                        hintText: 'Describe your legal question…',
                        isDense: true,
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 12,
                        ),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(22),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  IconButton.filled(
                    onPressed: chat.sending ? null : () => _send(),
                    icon: chat.sending
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _welcome(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(18),
      children: [
        const SizedBox(height: 10),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.navy,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(
                Icons.auto_awesome,
                color: AppColors.tealBright,
                size: 26,
              ),
              const SizedBox(height: 10),
              const Text(
                'Your Indian legal assistant',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 19,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                'Answers are synthesized only from statutory provisions retrieved from the Vidhik database. '
                'Every response lists its sources so you can verify the law. If synthesis is unavailable, '
                'the retrieved provisions are still shown.',
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.78),
                  fontSize: 12.5,
                  height: 1.5,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),
        const SectionTitle('Try asking'),
        for (final suggestion in _suggestions)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: AppCard(
              onTap: () => _send(suggestion),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Row(
                children: [
                  const Icon(
                    Icons.arrow_forward_ios,
                    size: 12,
                    color: AppColors.teal,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      suggestion,
                      style: const TextStyle(fontSize: 13, height: 1.35),
                    ),
                  ),
                ],
              ),
            ),
          ),
        const SizedBox(height: 10),
        const Text(
          'Do not include passwords, OTPs or unnecessary personal data in your question.',
          style: TextStyle(fontSize: 11, color: AppColors.muted),
        ),
      ],
    );
  }
}

class _TurnBubble extends StatelessWidget {
  const _TurnBubble({required this.turn});

  final ChatTurn turn;

  @override
  Widget build(BuildContext context) {
    if (turn.isUser) {
      return Align(
        alignment: Alignment.centerRight,
        child: Container(
          constraints: BoxConstraints(
            maxWidth: MediaQuery.of(context).size.width * 0.82,
          ),
          margin: const EdgeInsets.only(bottom: 12, left: 36),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
          decoration: const BoxDecoration(
            color: AppColors.navy,
            borderRadius: BorderRadius.only(
              topLeft: Radius.circular(15),
              topRight: Radius.circular(15),
              bottomLeft: Radius.circular(15),
              bottomRight: Radius.circular(4),
            ),
          ),
          child: Text(
            turn.content,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 13.5,
              height: 1.45,
            ),
          ),
        ),
      );
    }

    final isError = turn.isError;
    return Container(
      margin: const EdgeInsets.only(bottom: 14, right: 22),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isError
            ? AppColors.danger.withValues(alpha: 0.05)
            : Theme.of(context).colorScheme.surface,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(4),
          topRight: Radius.circular(15),
          bottomLeft: Radius.circular(15),
          bottomRight: Radius.circular(15),
        ),
        border: Border.all(
          color: isError
              ? AppColors.danger.withValues(alpha: 0.3)
              : AppColors.border,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                isError ? Icons.error_outline : Icons.gavel,
                size: 16,
                color: isError ? AppColors.danger : AppColors.teal,
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  isError ? 'Connection problem' : turn.groundingLabel,
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: isError ? AppColors.danger : AppColors.muted,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          SelectableText(
            turn.content,
            style: const TextStyle(fontSize: 13.5, height: 1.55),
          ),
          if (turn.sources.isNotEmpty) ...[
            const SizedBox(height: 12),
            ExpansionTile(
              tilePadding: EdgeInsets.zero,
              childrenPadding: EdgeInsets.zero,
              shape: const Border(),
              leading: const Icon(
                Icons.menu_book_outlined,
                size: 18,
                color: AppColors.teal,
              ),
              title: Text(
                '${turn.sources.length} statutory source${turn.sources.length == 1 ? '' : 's'}',
                style: const TextStyle(
                  fontSize: 12.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
              children: [
                for (final source in turn.sources)
                  Container(
                    width: double.infinity,
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppColors.background,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          source.citationLine,
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            height: 1.35,
                          ),
                        ),
                        if (source.jurisdiction != null)
                          Text(
                            'Jurisdiction: ${source.jurisdiction}',
                            style: const TextStyle(
                              fontSize: 10.5,
                              color: AppColors.muted,
                            ),
                          ),
                        if (source.sourcePdf != null)
                          Text(
                            'Source: ${source.sourcePdf}'
                            '${source.pageStart != null ? ' · page ${source.pageStart}' : ''}',
                            style: const TextStyle(
                              fontSize: 10.5,
                              color: AppColors.muted,
                            ),
                          ),
                      ],
                    ),
                  ),
                if (turn.provisions.isNotEmpty)
                  for (final provision in turn.provisions)
                    Container(
                      width: double.infinity,
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: AppColors.border),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${provision.lawName} — Section ${provision.sectionNumber}',
                            style: const TextStyle(
                              fontSize: 11.5,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          if (provision.sectionTitle != null)
                            Text(
                              provision.sectionTitle!,
                              style: const TextStyle(
                                fontSize: 11,
                                color: AppColors.muted,
                              ),
                            ),
                          const SizedBox(height: 6),
                          Text(
                            provision.sectionText.length > 700
                                ? '${provision.sectionText.substring(0, 700)}…'
                                : provision.sectionText,
                            style: const TextStyle(
                              fontSize: 11.5,
                              height: 1.45,
                            ),
                          ),
                        ],
                      ),
                    ),
              ],
            ),
          ],
          if (turn.disclaimer != null && turn.disclaimer!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              turn.disclaimer!,
              style: const TextStyle(
                fontSize: 10,
                color: AppColors.muted,
                height: 1.4,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _TypingBubble extends StatelessWidget {
  const _TypingBubble();

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 14, right: 60),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            width: 15,
            height: 15,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
          SizedBox(width: 10),
          Text(
            'Retrieving statutory provisions…',
            style: TextStyle(fontSize: 12, color: AppColors.muted),
          ),
        ],
      ),
    );
  }
}
