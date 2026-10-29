import '../core/utils/format.dart';

/// Statutory citation returned by the grounded RAG assistant.
class LegalCitation {
  final int lawId;
  final String lawName;
  final int sectionId;
  final String sectionNumber;
  final String? sectionTitle;
  final String? sourcePdf;
  final int? pageStart;
  final int? pageEnd;
  final String? jurisdiction;

  const LegalCitation({
    required this.lawId,
    required this.lawName,
    required this.sectionId,
    required this.sectionNumber,
    this.sectionTitle,
    this.sourcePdf,
    this.pageStart,
    this.pageEnd,
    this.jurisdiction,
  });

  String get label => 'Section $sectionNumber';
  String get citationLine {
    final title = (sectionTitle ?? '').trim();
    return title.isEmpty
        ? '$lawName — Section $sectionNumber'
        : '$lawName — Section $sectionNumber: $title';
  }

  factory LegalCitation.fromJson(dynamic json) {
    final map = asMap(json);
    return LegalCitation(
      lawId: asInt(map['law_id']),
      lawName: asString(map['law_name']),
      sectionId: asInt(map['section_id']),
      sectionNumber: asString(map['section_number']),
      sectionTitle: asString(map['section_title']).isEmpty
          ? null
          : asString(map['section_title']),
      sourcePdf: asString(map['source_pdf']).isEmpty
          ? null
          : asString(map['source_pdf']),
      pageStart: map['source_page_start'] == null
          ? null
          : asInt(map['source_page_start']),
      pageEnd: map['source_page_end'] == null
          ? null
          : asInt(map['source_page_end']),
      jurisdiction: asString(map['jurisdiction']).isEmpty
          ? null
          : asString(map['jurisdiction']),
    );
  }
}

class RetrievedProvision {
  final String lawName;
  final String sectionNumber;
  final String? sectionTitle;
  final String sectionText;
  final int rank;
  final String? relevanceExplanation;
  final LegalCitation? source;

  const RetrievedProvision({
    required this.lawName,
    required this.sectionNumber,
    required this.sectionText,
    required this.rank,
    this.sectionTitle,
    this.relevanceExplanation,
    this.source,
  });

  factory RetrievedProvision.fromJson(dynamic json) {
    final map = asMap(json);
    return RetrievedProvision(
      lawName: asString(map['law_name']),
      sectionNumber: asString(map['section_number']),
      sectionTitle: asString(map['section_title']).isEmpty
          ? null
          : asString(map['section_title']),
      sectionText: asString(map['section_text']),
      rank: asInt(map['relevance_rank'], 1),
      relevanceExplanation: asString(map['relevance_explanation']).isEmpty
          ? null
          : asString(map['relevance_explanation']),
      source: map['source'] is Map
          ? LegalCitation.fromJson(map['source'])
          : null,
    );
  }
}

/// A single chat turn displayed in the assistant UI.
class ChatTurn {
  final String role; // 'user' | 'assistant'
  final String content;
  final DateTime createdAt;
  final List<LegalCitation> sources;
  final List<RetrievedProvision> provisions;
  final String? groundingStatus;
  final bool isGrounded;
  final String? disclaimer;
  final String? conversationId;
  final bool isError;

  ChatTurn({
    required this.role,
    required this.content,
    DateTime? createdAt,
    this.sources = const [],
    this.provisions = const [],
    this.groundingStatus,
    this.isGrounded = false,
    this.disclaimer,
    this.conversationId,
    this.isError = false,
  }) : createdAt = createdAt ?? DateTime.now();

  bool get isUser => role == 'user';

  String get groundingLabel {
    switch (groundingStatus) {
      case 'grounded_high':
        return 'Grounded • High confidence';
      case 'grounded_medium':
        return 'Grounded • Medium confidence';
      case 'synthesis_failed':
        return 'Statutes retrieved • AI synthesis unavailable';
      case 'no_context':
        return 'No matching statute found';
      case 'insufficient_context':
        return 'Limited statutory context';
      case 'safety_refusal':
        return 'Safety refusal';
      default:
        return 'Assistant response';
    }
  }
}

class AssistantReply {
  final String conversationId;
  final String answer;
  final String language;
  final String groundingStatus;
  final bool isGrounded;
  final List<LegalCitation> sources;
  final List<RetrievedProvision> provisions;
  final String disclaimer;

  const AssistantReply({
    required this.conversationId,
    required this.answer,
    required this.language,
    required this.groundingStatus,
    required this.isGrounded,
    required this.sources,
    required this.provisions,
    required this.disclaimer,
  });

  factory AssistantReply.fromJson(dynamic json) {
    final map = asMap(json);
    return AssistantReply(
      conversationId: asString(map['conversation_id']),
      answer: asString(map['answer']),
      language: firstNonEmpty([map['language'], 'en']),
      groundingStatus: firstNonEmpty([
        map['grounding_status'],
        map['confidence'],
        'unknown',
      ]),
      isGrounded: asBool(map['is_grounded']),
      sources: asMapList(map['sources']).map(LegalCitation.fromJson).toList(),
      provisions: asMapList(map['retrieved_sections'])
          .map(RetrievedProvision.fromJson)
          .toList(),
      disclaimer: asString(map['disclaimer']),
    );
  }
}
