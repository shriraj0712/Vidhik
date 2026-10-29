import '../core/utils/format.dart';

class CitizenDashboard {
  final int activeCases;
  final int totalCases;
  final int documentsCount;
  final int upcomingHearingsCount;
  final int unreadNotificationsCount;
  final int recentAnalysesCount;
  final int savedSectionsCount;
  final int trackedProceduresCount;
  final List<Map<String, dynamic>> recentCases;
  final List<Map<String, dynamic>> upcomingHearings;
  final List<Map<String, dynamic>> recentDocuments;
  final List<Map<String, dynamic>> recentAnalyses;
  final List<Map<String, dynamic>> recentNotifications;

  const CitizenDashboard({
    required this.activeCases,
    required this.totalCases,
    required this.documentsCount,
    required this.upcomingHearingsCount,
    required this.unreadNotificationsCount,
    required this.recentAnalysesCount,
    required this.savedSectionsCount,
    required this.trackedProceduresCount,
    this.recentCases = const [],
    this.upcomingHearings = const [],
    this.recentDocuments = const [],
    this.recentAnalyses = const [],
    this.recentNotifications = const [],
  });

  factory CitizenDashboard.fromJson(dynamic json) {
    final map = asMap(json);
    return CitizenDashboard(
      activeCases: asInt(map['active_cases']),
      totalCases: asInt(map['total_cases']),
      documentsCount: asInt(map['documents_count']),
      upcomingHearingsCount: asInt(map['upcoming_hearings_count']),
      unreadNotificationsCount: asInt(map['unread_notifications_count']),
      recentAnalysesCount: asInt(map['recent_analyses_count']),
      savedSectionsCount: asInt(map['saved_sections_count']),
      trackedProceduresCount: asInt(map['tracked_procedures_count']),
      recentCases: asMapList(map['recent_cases']),
      upcomingHearings: asMapList(map['upcoming_hearings']),
      recentDocuments: asMapList(map['recent_documents']),
      recentAnalyses: asMapList(map['recent_analyses']),
      recentNotifications: asMapList(
        map['recent_notifications'].isNotEmpty == true
            ? map['recent_notifications']
            : map['notifications'],
      ),
    );
  }
}

class CitizenCase {
  final int caseId;
  final String title;
  final String? caseNumber;
  final String? caseType;
  final String? courtName;
  final String? oppositeParty;
  final String status;
  final String? description;
  final String? cnrNumber;
  final String? officialCaseUrl;
  final String? externalStatus;
  final String? nextHearingDate;
  final String? assignedLawyerName;
  final String? location;
  final String? policeStation;
  final int documentsCount;
  final int hearingsCount;
  final String? createdAt;

  const CitizenCase({
    required this.caseId,
    required this.title,
    this.caseNumber,
    this.caseType,
    this.courtName,
    this.oppositeParty,
    required this.status,
    this.description,
    this.cnrNumber,
    this.officialCaseUrl,
    this.externalStatus,
    this.nextHearingDate,
    this.assignedLawyerName,
    this.location,
    this.policeStation,
    this.documentsCount = 0,
    this.hearingsCount = 0,
    this.createdAt,
  });

  factory CitizenCase.fromJson(dynamic json) {
    final map = asMap(json);
    return CitizenCase(
      caseId: asInt(map['case_id']),
      title: firstNonEmpty([
        map['case_title'],
        map['title'],
        'Untitled matter',
      ]),
      caseNumber: asString(map['case_number']).isEmpty
          ? null
          : asString(map['case_number']),
      caseType: asString(map['case_type']).isEmpty
          ? null
          : asString(map['case_type']),
      courtName: firstNonEmpty([map['court_name'], map['court']]).isEmpty
          ? null
          : firstNonEmpty([map['court_name'], map['court']]),
      oppositeParty: asString(map['opposite_party']).isEmpty
          ? null
          : asString(map['opposite_party']),
      status: firstNonEmpty([map['status'], 'active']),
      description:
          firstNonEmpty([map['case_description'], map['description']]).isEmpty
          ? null
          : firstNonEmpty([map['case_description'], map['description']]),
      cnrNumber: asString(map['cnr_number']).isEmpty
          ? null
          : asString(map['cnr_number']),
      officialCaseUrl: asString(map['official_case_url']).isEmpty
          ? null
          : asString(map['official_case_url']),
      externalStatus: asString(map['external_status']).isEmpty
          ? null
          : asString(map['external_status']),
      nextHearingDate: asString(map['external_next_hearing_date']).isEmpty
          ? null
          : asString(map['external_next_hearing_date']),
      assignedLawyerName:
          firstNonEmpty([map['assigned_lawyer_name'], map['lawyer_name']])
              .isEmpty
          ? null
          : firstNonEmpty([map['assigned_lawyer_name'], map['lawyer_name']]),
      location: asString(map['location']).isEmpty
          ? null
          : asString(map['location']),
      policeStation: asString(map['police_station']).isEmpty
          ? null
          : asString(map['police_station']),
      documentsCount: asInt(map['documents_count']),
      hearingsCount: asInt(map['hearings_count']),
      createdAt: asString(map['created_at']).isEmpty
          ? null
          : asString(map['created_at']),
    );
  }
}

class CitizenDocument {
  final int documentId;
  final int caseId;
  final String? caseTitle;
  final String documentName;
  final String documentType;
  final String filePath;
  final int fileSizeBytes;
  final String mimeType;
  final String uploadStatus;
  final String? description;
  final String? createdAt;

  const CitizenDocument({
    required this.documentId,
    required this.caseId,
    this.caseTitle,
    required this.documentName,
    required this.documentType,
    required this.filePath,
    required this.fileSizeBytes,
    required this.mimeType,
    required this.uploadStatus,
    this.description,
    this.createdAt,
  });

  factory CitizenDocument.fromJson(dynamic json) {
    final map = asMap(json);
    return CitizenDocument(
      documentId: asInt(map['document_id']),
      caseId: asInt(map['case_id']),
      caseTitle: asString(map['case_title']).isEmpty
          ? null
          : asString(map['case_title']),
      documentName: firstNonEmpty([map['document_name'], 'Document']),
      documentType: firstNonEmpty([map['document_type'], 'General']),
      filePath: asString(map['file_path']),
      fileSizeBytes: asInt(map['file_size_bytes']),
      mimeType: firstNonEmpty([map['mime_type'], 'application/octet-stream']),
      uploadStatus: firstNonEmpty([map['upload_status'], 'uploaded']),
      description: asString(map['description']).isEmpty
          ? null
          : asString(map['description']),
      createdAt: asString(map['created_at']).isEmpty
          ? null
          : asString(map['created_at']),
    );
  }

  String get readableSize {
    if (fileSizeBytes <= 0) return '—';
    if (fileSizeBytes < 1024) return '$fileSizeBytes B';
    if (fileSizeBytes < 1024 * 1024) {
      return '${(fileSizeBytes / 1024).toStringAsFixed(1)} KB';
    }
    return '${(fileSizeBytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }
}

class CitizenNotification {
  final int notificationId;
  final String title;
  final String message;
  final String? notificationType;
  final bool isRead;
  final String? createdAt;

  const CitizenNotification({
    required this.notificationId,
    required this.title,
    required this.message,
    this.notificationType,
    required this.isRead,
    this.createdAt,
  });

  factory CitizenNotification.fromJson(dynamic json) {
    final map = asMap(json);
    return CitizenNotification(
      notificationId: asInt(map['notification_id']),
      title: firstNonEmpty([map['title'], 'Notification']),
      message: asString(map['message']),
      notificationType: asString(map['notification_type']).isEmpty
          ? null
          : asString(map['notification_type']),
      isRead: asBool(map['is_read']),
      createdAt: firstNonEmpty([map['created_at'], map['sent_at']]),
    );
  }
}

class BookmarkedSection {
  final int bookmarkId;
  final int sectionId;
  final int lawId;
  final String sectionNumber;
  final String? sectionTitle;
  final String? lawName;
  final String? createdAt;

  const BookmarkedSection({
    required this.bookmarkId,
    required this.sectionId,
    required this.lawId,
    required this.sectionNumber,
    this.sectionTitle,
    this.lawName,
    this.createdAt,
  });

  factory BookmarkedSection.fromJson(dynamic json) {
    final map = asMap(json);
    return BookmarkedSection(
      bookmarkId: asInt(map['bookmark_id']),
      sectionId: asInt(map['section_id']),
      lawId: asInt(map['law_id']),
      sectionNumber: asString(map['section_number']),
      sectionTitle: asString(map['section_title']).isEmpty
          ? null
          : asString(map['section_title']),
      lawName: asString(map['law_name']).isEmpty
          ? null
          : asString(map['law_name']),
      createdAt: asString(map['created_at']).isEmpty
          ? null
          : asString(map['created_at']),
    );
  }
}

class SearchHistoryEntry {
  final int historyId;
  final String queryText;
  final int? resultsCount;
  final String? createdAt;

  const SearchHistoryEntry({
    required this.historyId,
    required this.queryText,
    this.resultsCount,
    this.createdAt,
  });

  factory SearchHistoryEntry.fromJson(dynamic json) {
    final map = asMap(json);
    return SearchHistoryEntry(
      historyId: asInt(map['history_id']),
      queryText: firstNonEmpty([map['query_text'], map['query'], '']),
      resultsCount: map['results_count'] == null
          ? null
          : asInt(map['results_count']),
      createdAt: firstNonEmpty([map['created_at'], map['searched_at']]),
    );
  }
}

class ProcedureTracker {
  final int trackerId;
  final int procedureId;
  final String procedureName;
  final String category;
  final String status;
  final List<String> completedDocuments;
  final int totalDocumentsCount;
  final int completedDocumentsCount;
  final String? notes;
  final String? updatedAt;

  const ProcedureTracker({
    required this.trackerId,
    required this.procedureId,
    required this.procedureName,
    required this.category,
    required this.status,
    this.completedDocuments = const [],
    this.totalDocumentsCount = 0,
    this.completedDocumentsCount = 0,
    this.notes,
    this.updatedAt,
  });

  double get progress => totalDocumentsCount == 0
      ? 0
      : completedDocumentsCount / totalDocumentsCount;

  factory ProcedureTracker.fromJson(dynamic json) {
    final map = asMap(json);
    final docs = map['completed_documents'];
    return ProcedureTracker(
      trackerId: asInt(map['tracker_id']),
      procedureId: asInt(map['procedure_id']),
      procedureName: firstNonEmpty([map['procedure_name'], 'Procedure']),
      category: asString(map['category']),
      status: firstNonEmpty([map['status'], 'in_progress']),
      completedDocuments: docs is List
          ? docs.map((e) => asString(e)).where((e) => e.isNotEmpty).toList()
          : const [],
      totalDocumentsCount: asInt(map['total_documents_count']),
      completedDocumentsCount: asInt(map['completed_documents_count']),
      notes: asString(map['notes']).isEmpty ? null : asString(map['notes']),
      updatedAt: asString(map['updated_at']).isEmpty
          ? null
          : asString(map['updated_at']),
    );
  }
}

class CitizenProfile {
  final int userId;
  final String fullName;
  final String email;
  final String? phone;
  final String? dateOfBirth;
  final String? address;
  final String? city;
  final String? state;
  final String? pincode;
  final String preferredLanguage;
  final String? occupation;
  final String? emergencyContact;
  final String? createdAt;

  const CitizenProfile({
    required this.userId,
    required this.fullName,
    required this.email,
    this.phone,
    this.dateOfBirth,
    this.address,
    this.city,
    this.state,
    this.pincode,
    this.preferredLanguage = 'en',
    this.occupation,
    this.emergencyContact,
    this.createdAt,
  });

  factory CitizenProfile.fromJson(dynamic json) {
    final map = asMap(json);
    return CitizenProfile(
      userId: asInt(map['user_id']),
      fullName: asString(map['full_name']),
      email: asString(map['email']),
      phone: asString(map['phone']).isEmpty ? null : asString(map['phone']),
      dateOfBirth: asString(map['date_of_birth']).isEmpty
          ? null
          : asString(map['date_of_birth']),
      address: asString(map['address']).isEmpty
          ? null
          : asString(map['address']),
      city: asString(map['city']).isEmpty ? null : asString(map['city']),
      state: asString(map['state']).isEmpty ? null : asString(map['state']),
      pincode: asString(map['pincode']).isEmpty
          ? null
          : asString(map['pincode']),
      preferredLanguage: firstNonEmpty([map['preferred_language'], 'en']),
      occupation: asString(map['occupation']).isEmpty
          ? null
          : asString(map['occupation']),
      emergencyContact: asString(map['emergency_contact']).isEmpty
          ? null
          : asString(map['emergency_contact']),
      createdAt: asString(map['created_at']).isEmpty
          ? null
          : asString(map['created_at']),
    );
  }
}
