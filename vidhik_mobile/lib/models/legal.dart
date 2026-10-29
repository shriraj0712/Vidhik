import '../core/utils/format.dart';

class LegalSearchResult {
  final int lawId;
  final String lawName;
  final int sectionId;
  final String sectionNumber;
  final String? sectionTitle;
  final String? snippet;
  final String? jurisdiction;
  final String? sourcePdf;
  final bool manualReviewRequired;

  const LegalSearchResult({
    required this.lawId,
    required this.lawName,
    required this.sectionId,
    required this.sectionNumber,
    this.sectionTitle,
    this.snippet,
    this.jurisdiction,
    this.sourcePdf,
    this.manualReviewRequired = false,
  });

  factory LegalSearchResult.fromJson(dynamic json) {
    final map = asMap(json);
    return LegalSearchResult(
      lawId: asInt(map['law_id']),
      lawName: asString(map['law_name']),
      sectionId: asInt(map['section_id']),
      sectionNumber: asString(map['section_number']),
      sectionTitle: asString(map['section_title']).isEmpty
          ? null
          : asString(map['section_title']),
      snippet: asString(map['snippet']).isEmpty
          ? null
          : asString(map['snippet']),
      jurisdiction: asString(map['jurisdiction']).isEmpty
          ? null
          : asString(map['jurisdiction']),
      sourcePdf: asString(map['source_pdf']).isEmpty
          ? null
          : asString(map['source_pdf']),
      manualReviewRequired: asBool(map['manual_review_required']),
    );
  }
}

class LegalSearchPage {
  final String query;
  final int total;
  final int limit;
  final int offset;
  final List<LegalSearchResult> results;

  const LegalSearchPage({
    required this.query,
    required this.total,
    required this.limit,
    required this.offset,
    required this.results,
  });

  factory LegalSearchPage.fromJson(dynamic json) {
    final map = asMap(json);
    return LegalSearchPage(
      query: asString(map['query']),
      total: asInt(map['total']),
      limit: asInt(map['limit'], 20),
      offset: asInt(map['offset']),
      results: asMapList(map['results'])
          .map(LegalSearchResult.fromJson)
          .toList(),
    );
  }
}

class StatuteSection {
  final int sectionId;
  final int lawId;
  final String sectionNumber;
  final String? sectionTitle;
  final String? fullText;
  final String? chapter;
  final String? jurisdiction;
  final String? sourcePdf;
  final int? pageStart;
  final int? pageEnd;
  final bool isOmitted;
  final String? omissionNote;

  const StatuteSection({
    required this.sectionId,
    required this.lawId,
    required this.sectionNumber,
    this.sectionTitle,
    this.fullText,
    this.chapter,
    this.jurisdiction,
    this.sourcePdf,
    this.pageStart,
    this.pageEnd,
    this.isOmitted = false,
    this.omissionNote,
  });

  String get text => cleanLegalText(fullText);

  factory StatuteSection.fromJson(dynamic json) {
    final map = asMap(json);
    return StatuteSection(
      sectionId: asInt(map['section_id']),
      lawId: asInt(map['law_id']),
      sectionNumber: asString(map['section_number']),
      sectionTitle: asString(map['section_title']).isEmpty
          ? null
          : asString(map['section_title']),
      fullText: firstNonEmpty([
        map['full_text'],
        map['section_text'],
        map['description'],
      ]),
      chapter: firstNonEmpty([map['chapter_title'], map['chapter']]),
      jurisdiction: asString(map['jurisdiction']).isEmpty
          ? null
          : asString(map['jurisdiction']),
      sourcePdf: asString(map['source_pdf']).isEmpty
          ? null
          : asString(map['source_pdf']),
      pageStart: map['page_start'] != null
          ? asInt(map['page_start'])
          : (map['source_page_start'] != null
                ? asInt(map['source_page_start'])
                : null),
      pageEnd: map['page_end'] != null
          ? asInt(map['page_end'])
          : (map['source_page_end'] != null
                ? asInt(map['source_page_end'])
                : null),
      isOmitted: asBool(map['is_omitted']),
      omissionNote: asString(map['omission_note']).isEmpty
          ? null
          : asString(map['omission_note']),
    );
  }
}

class LawAct {
  final int actId;
  final String actName;
  final String shortName;
  final String? actNumber;
  final int year;
  final String category;
  final String status;
  final int totalSections;
  final int offencesCount;
  final int punishmentsCount;
  final int proceduresCount;
  final int evidenceCount;
  final bool hasOffences;
  final String jurisdiction;
  final String? amendmentDetails;
  final String judgmentsStatus;
  final List<String> authorities;

  const LawAct({
    required this.actId,
    required this.actName,
    required this.shortName,
    this.actNumber,
    required this.year,
    required this.category,
    required this.status,
    required this.totalSections,
    required this.offencesCount,
    required this.punishmentsCount,
    required this.proceduresCount,
    required this.evidenceCount,
    required this.hasOffences,
    required this.jurisdiction,
    this.amendmentDetails,
    required this.judgmentsStatus,
    this.authorities = const [],
  });

  factory LawAct.fromJson(dynamic json) {
    final map = asMap(json);
    final authorities = map['authorities'];
    return LawAct(
      actId: asInt(map['act_id']),
      actName: asString(map['act_name']),
      shortName: firstNonEmpty([map['short_name'], map['act_name']]),
      actNumber: asString(map['act_number']).isEmpty
          ? null
          : asString(map['act_number']),
      year: asInt(map['year']),
      category: asString(map['category']),
      status: firstNonEmpty([map['status'], 'In Force']),
      totalSections: asInt(map['total_sections']),
      offencesCount: asInt(map['offences_count']),
      punishmentsCount: asInt(map['punishments_count']),
      proceduresCount: asInt(map['procedures_count']),
      evidenceCount: asInt(map['evidence_count']),
      hasOffences: asBool(map['has_offences']),
      jurisdiction: firstNonEmpty([map['jurisdiction'], 'Central / India']),
      amendmentDetails: asString(map['amendment_details']).isEmpty
          ? null
          : asString(map['amendment_details']),
      judgmentsStatus: firstNonEmpty([
        map['judgments_status'],
        'NOT IN SOURCE',
      ]),
      authorities: authorities is List
          ? authorities
                .map((e) => asString(e))
                .where((e) => e.isNotEmpty)
                .toList()
          : const [],
    );
  }
}

class KnowledgeOverview {
  final String status;
  final String corpus;
  final List<String> supportedStatutes;
  final int totalOffences;
  final int totalPunishments;
  final int totalProcedures;
  final int totalEvidenceProvisions;
  final int totalPredecessorMappings;
  final int totalVerifiedJudgments;
  final Map<String, int> categories;

  const KnowledgeOverview({
    required this.status,
    required this.corpus,
    required this.supportedStatutes,
    required this.totalOffences,
    required this.totalPunishments,
    required this.totalProcedures,
    required this.totalEvidenceProvisions,
    required this.totalPredecessorMappings,
    required this.totalVerifiedJudgments,
    required this.categories,
  });

  factory KnowledgeOverview.fromJson(dynamic json) {
    final map = asMap(json);
    final statutes = map['supported_statutes'];
    final categoryMap = asMap(map['categories']);
    return KnowledgeOverview(
      status: asString(map['status']),
      corpus: asString(map['corpus']),
      supportedStatutes: statutes is List
          ? statutes.map((e) => asString(e)).where((e) => e.isNotEmpty).toList()
          : const [],
      totalOffences: asInt(map['total_offences']),
      totalPunishments: asInt(map['total_punishments']),
      totalProcedures: asInt(map['total_procedures']),
      totalEvidenceProvisions: asInt(map['total_evidence_provisions']),
      totalPredecessorMappings: asInt(map['total_predecessor_mappings']),
      totalVerifiedJudgments: asInt(map['total_verified_judgments']),
      categories: categoryMap.map((key, value) => MapEntry(key, asInt(value))),
    );
  }
}

class LegalProcedure {
  final int procedureId;
  final String procedureName;
  final String procedureSlug;
  final String category;
  final String description;
  final String jurisdiction;
  final String authorityType;
  final int? estimatedProcessingDays;
  final String? officialPortalUrl;
  final String? governingLawName;
  final String? governingSectionNumber;
  final int totalDocumentsCount;
  final int mandatoryDocumentsCount;

  const LegalProcedure({
    required this.procedureId,
    required this.procedureName,
    required this.procedureSlug,
    required this.category,
    required this.description,
    required this.jurisdiction,
    required this.authorityType,
    this.estimatedProcessingDays,
    this.officialPortalUrl,
    this.governingLawName,
    this.governingSectionNumber,
    required this.totalDocumentsCount,
    required this.mandatoryDocumentsCount,
  });

  factory LegalProcedure.fromJson(dynamic json) {
    final map = asMap(json);
    return LegalProcedure(
      procedureId: asInt(map['procedure_id']),
      procedureName: asString(map['procedure_name']),
      procedureSlug: asString(map['procedure_slug']),
      category: asString(map['category']),
      description: asString(map['description']),
      jurisdiction: firstNonEmpty([map['jurisdiction'], 'India']),
      authorityType: asString(map['authority_type']),
      estimatedProcessingDays: map['estimated_processing_days'] == null
          ? null
          : asInt(map['estimated_processing_days']),
      officialPortalUrl: asString(map['official_portal_url']).isEmpty
          ? null
          : asString(map['official_portal_url']),
      governingLawName: asString(map['governing_law_name']).isEmpty
          ? null
          : asString(map['governing_law_name']),
      governingSectionNumber: asString(map['governing_section_number']).isEmpty
          ? null
          : asString(map['governing_section_number']),
      totalDocumentsCount: asInt(map['total_documents_count']),
      mandatoryDocumentsCount: asInt(map['mandatory_documents_count']),
    );
  }
}

class DocumentRequirement {
  final String documentName;
  final String documentType;
  final bool isMandatory;
  final String purpose;
  final String? preparationGuidance;
  final String? sectionNumber;
  final String? lawName;

  const DocumentRequirement({
    required this.documentName,
    required this.documentType,
    required this.isMandatory,
    required this.purpose,
    this.preparationGuidance,
    this.sectionNumber,
    this.lawName,
  });

  factory DocumentRequirement.fromJson(dynamic json) {
    final map = asMap(json);
    return DocumentRequirement(
      documentName: asString(map['document_name']),
      documentType: asString(map['document_type']),
      isMandatory: asBool(map['is_mandatory']),
      purpose: asString(map['purpose']),
      preparationGuidance: asString(map['preparation_guidance']).isEmpty
          ? null
          : asString(map['preparation_guidance']),
      sectionNumber: asString(map['section_number']).isEmpty
          ? null
          : asString(map['section_number']),
      lawName: asString(map['law_name']).isEmpty
          ? null
          : asString(map['law_name']),
    );
  }
}
