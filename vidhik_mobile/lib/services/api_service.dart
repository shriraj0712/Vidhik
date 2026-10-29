import '../core/network/api_client.dart';
import '../core/utils/format.dart';
import '../models/auth_user.dart';
import '../models/chat.dart';
import '../models/citizen.dart';
import '../models/legal.dart';

/// Thin, typed facade over the existing VIDHIK FastAPI contract.
///
/// Every path here exists in `backend/app/routers`. No new backend contract is
/// invented for the mobile client.
class ApiService {
  ApiService(this.client);

  final ApiClient client;

  // ---------------------------------------------------------------------
  // Authentication & security
  // ---------------------------------------------------------------------

  Future<Map<String, dynamic>> turnstileConfig() async =>
      asMap(await client.get('/api/auth/turnstile-config'));

  Future<Map<String, dynamic>> googleConfig() async =>
      asMap(await client.get('/api/auth/google-config'));

  Future<RegistrationInitiation> registerInitiate({
    required String fullName,
    required String email,
    required String password,
    String? confirmPassword,
    String? phone,
    String? turnstileToken,
  }) async {
    final data = await client.post(
      '/api/auth/register-initiate',
      body: {
        'full_name': fullName.trim(),
        'email': email.trim(),
        'phone': (phone ?? '').trim().isEmpty ? null : phone!.trim(),
        'password': password,
        'confirm_password': confirmPassword ?? password,
        'turnstile_token': turnstileToken,
      },
    );
    return RegistrationInitiation.fromJson(data);
  }

  Future<TwoFactorEnrollment> verifyOtp({
    required String target,
    required String otpCode,
    String purpose = 'signup_verification',
  }) async {
    final data = await client.post(
      '/api/auth/verify-otp',
      body: {'target': target, 'otp_code': otpCode, 'purpose': purpose},
    );
    return TwoFactorEnrollment.fromJson(data);
  }

  Future<Map<String, dynamic>> resendOtp({
    required String target,
    String purpose = 'signup_verification',
    String? turnstileToken,
  }) async => asMap(
    await client.post(
      '/api/auth/resend-otp',
      body: {
        'target': target,
        'purpose': purpose,
        'turnstile_token': turnstileToken,
      },
    ),
  );

  Future<AuthSession> completeTwoFactorSetup({
    required String setupToken,
    required String totpCode,
  }) async {
    final data = await client.post(
      '/api/auth/2fa/setup-verify',
      body: {'two_factor_setup_token': setupToken, 'totp_code': totpCode},
    );
    return AuthSession.fromJson(data);
  }

  Future<AuthChallenge> login({
    required String identifier,
    required String password,
    String? turnstileToken,
  }) async {
    final data = await client.post(
      '/api/auth/login',
      body: {
        'identifier': identifier.trim(),
        'email': identifier.trim(),
        'password': password,
        'turnstile_token': turnstileToken,
      },
    );
    return AuthChallenge.fromJson(data);
  }

  Future<AuthSession> verifyTwoFactorLogin({
    required String twoFactorToken,
    required String code,
    bool useRecoveryCode = false,
  }) async {
    final data = await client.post(
      '/api/auth/2fa/verify-login',
      body: {
        'two_factor_token': twoFactorToken,
        'totp_code': code,
        'code': code,
        'use_recovery_code': useRecoveryCode,
      },
    );
    return AuthSession.fromJson(data);
  }

  Future<AuthChallenge> googleLogin({
    required String idToken,
    String? turnstileToken,
  }) async {
    final data = await client.post(
      '/api/auth/google',
      body: {'id_token': idToken, 'turnstile_token': turnstileToken},
    );
    return AuthChallenge.fromJson(data);
  }

  Future<Map<String, dynamic>> forgotPassword({
    required String email,
    String? turnstileToken,
  }) async => asMap(
    await client.post(
      '/api/auth/forgot-password',
      body: {'email': email, 'turnstile_token': turnstileToken},
    ),
  );

  Future<Map<String, dynamic>> resetPassword({
    required String email,
    required String otpCode,
    required String newPassword,
    required String confirmPassword,
    String? resetToken,
  }) async => asMap(
    await client.post(
      '/api/auth/reset-password',
      body: {
        'email': email,
        'otp_code': otpCode,
        'new_password': newPassword,
        'confirm_password': confirmPassword,
        'reset_token': resetToken,
      },
    ),
  );

  Future<AuthUser> me() async =>
      AuthUser.fromJson(await client.get('/api/auth/me'));

  Future<void> logout() async {
    await client.post('/api/auth/logout', body: const {});
  }

  Future<List<Map<String, dynamic>>> sessions() async {
    final data = await client.get('/api/auth/sessions');
    if (data is List) return asMapList(data);
    final map = asMap(data);
    return asMapList(map['active_sessions'] ?? map['sessions']);
  }

  Future<void> revokeSession(int sessionId) async {
    await client.delete('/api/auth/sessions/$sessionId');
  }

  Future<Map<String, dynamic>> revokeOtherSessions() async =>
      asMap(await client.delete('/api/auth/sessions/revoke-others'));

  Future<Map<String, dynamic>> securityAlerts() async =>
      asMap(await client.get('/api/auth/security-alerts'));

  Future<void> markSecurityAlertRead(int alertId) async {
    await client.post(
      '/api/auth/security-alerts/$alertId/read',
      body: const {},
    );
  }

  Future<Map<String, dynamic>> changePassword({
    required String currentPassword,
    required String newPassword,
    required String confirmPassword,
  }) async => asMap(
    await client.post(
      '/api/auth/password/change',
      body: {
        'current_password': currentPassword,
        'new_password': newPassword,
        'confirm_password': confirmPassword,
      },
    ),
  );

  Future<Map<String, dynamic>> regenerateRecoveryCodes({
    String? password,
    String? totpCode,
  }) async => asMap(
    await client.post(
      '/api/auth/2fa/regenerate-recovery-codes',
      body: {'password': password, 'totp_code': totpCode},
    ),
  );

  // ---------------------------------------------------------------------
  // AI assistant (grounded RAG)
  // ---------------------------------------------------------------------

  Future<AssistantReply> chat({
    required String message,
    String? conversationId,
    List<Map<String, dynamic>> history = const [],
    String language = 'en',
    int maxSections = 5,
    int? evidenceId,
  }) async {
    final data = await client.post(
      '/api/assistant/chat',
      body: {
        'message': message,
        'conversation_id': conversationId,
        'history': history,
        'language': language,
        'max_sections': maxSections,
        'evidence_id': evidenceId,
      },
      timeout: ApiClient.chatTimeout,
    );
    return AssistantReply.fromJson(data);
  }

  Future<Map<String, dynamic>> assistantHealth() async =>
      asMap(await client.get('/api/assistant/health'));

  // ---------------------------------------------------------------------
  // Citizen workspace
  // ---------------------------------------------------------------------

  Future<CitizenDashboard> citizenDashboard() async =>
      CitizenDashboard.fromJson(await client.get('/api/citizen/dashboard'));

  Future<List<CitizenCase>> citizenCases() async {
    final data = await client.get('/api/citizen/cases');
    return asMapList(data).map(CitizenCase.fromJson).toList();
  }

  Future<CitizenCase> citizenCaseDetail(int caseId) async =>
      CitizenCase.fromJson(await client.get('/api/citizen/cases/$caseId'));

  Future<Map<String, dynamic>> citizenCaseRaw(int caseId) async =>
      asMap(await client.get('/api/citizen/cases/$caseId'));

  Future<CitizenCase> createCitizenCase(Map<String, dynamic> body) async =>
      CitizenCase.fromJson(await client.post('/api/citizen/cases', body: body));

  Future<Map<String, dynamic>> updateCitizenCourtReference(
    int caseId,
    Map<String, dynamic> body,
  ) async => asMap(
    await client.patch(
      '/api/citizen/cases/$caseId/court-reference',
      body: body,
    ),
  );

  Future<List<CitizenDocument>> citizenDocuments() async {
    final data = await client.get('/api/citizen/documents');
    return asMapList(data).map(CitizenDocument.fromJson).toList();
  }

  Future<CitizenDocument> uploadCitizenDocument(
    Map<String, dynamic> body,
  ) async => CitizenDocument.fromJson(
    await client.post('/api/citizen/documents', body: body),
  );

  Future<List<Map<String, dynamic>>> citizenHearings() async =>
      asMapList(await client.get('/api/citizen/hearings'));

  Future<CitizenProfile> citizenProfile() async =>
      CitizenProfile.fromJson(await client.get('/api/citizen/profile'));

  Future<CitizenProfile> updateCitizenProfile(
    Map<String, dynamic> body,
  ) async => CitizenProfile.fromJson(
    await client.put('/api/citizen/profile', body: body),
  );

  Future<List<BookmarkedSection>> bookmarks() async {
    final data = await client.get('/api/citizen/bookmarks');
    return asMapList(data).map(BookmarkedSection.fromJson).toList();
  }

  Future<BookmarkedSection> addBookmark(int sectionId) async =>
      BookmarkedSection.fromJson(
        await client.post(
          '/api/citizen/bookmarks',
          body: {'section_id': sectionId},
        ),
      );

  Future<void> removeBookmark(int sectionId) async {
    await client.delete('/api/citizen/bookmarks/$sectionId');
  }

  Future<List<SearchHistoryEntry>> searchHistory({int limit = 50}) async {
    final data = await client.get(
      '/api/citizen/search-history',
      query: {'limit': limit},
    );
    return asMapList(data).map(SearchHistoryEntry.fromJson).toList();
  }

  Future<void> recordSearch(String queryText, int resultsCount) async {
    await client.post(
      '/api/citizen/search-history',
      body: {
        'query_text': queryText,
        'results_count': resultsCount,
        'search_filters': null,
      },
    );
  }

  Future<void> clearSearchHistory() async {
    await client.delete('/api/citizen/search-history');
  }

  Future<Map<String, dynamic>> notifications() async =>
      asMap(await client.get('/api/citizen/notifications'));

  Future<void> markNotificationRead(int id) async {
    await client.patch('/api/citizen/notifications/$id/read', body: const {});
  }

  Future<void> markAllNotificationsRead() async {
    await client.post('/api/citizen/notifications/read-all', body: const {});
  }

  Future<List<ProcedureTracker>> procedures() async {
    final data = await client.get('/api/citizen/procedures');
    return asMapList(data).map(ProcedureTracker.fromJson).toList();
  }

  Future<ProcedureTracker> toggleProcedureDocument({
    required int procedureId,
    required String documentName,
    bool? completed,
  }) async => ProcedureTracker.fromJson(
    await client.post(
      '/api/citizen/procedures/$procedureId/toggle-doc',
      body: {'document_name': documentName, 'completed': completed},
    ),
  );

  // ---------------------------------------------------------------------
  // Case intelligence
  // ---------------------------------------------------------------------

  Future<Map<String, dynamic>> activeCase() async =>
      asMap(await client.get('/api/cases/active'));

  Future<Map<String, dynamic>> createAndAnalyzeCase(
    Map<String, dynamic> body,
  ) async => asMap(
    await client.post(
      '/api/cases/create-and-analyze',
      body: body,
      timeout: const Duration(seconds: 150),
    ),
  );

  Future<Map<String, dynamic>> caseContext(int caseId) async =>
      asMap(await client.get('/api/cases/$caseId/context'));

  Future<List<Map<String, dynamic>>> caseLegalRanking(int caseId) async =>
      asMapList(await client.get('/api/cases/$caseId/legal-ranking'));

  Future<void> setActiveCase(int caseId) async {
    await client.post('/api/cases/$caseId/set-active', body: const {});
  }

  Future<Map<String, dynamic>> updateAndReanalyzeCase(
    int caseId,
    String additionalInformation, {
    String? location,
    String? oppositeParty,
    String? incidentDate,
  }) async => asMap(
    await client.post(
      '/api/cases/$caseId/update-and-reanalyze',
      body: {
        'additional_information': additionalInformation,
        'updated_location': location,
        'updated_opposite_party': oppositeParty,
        'updated_incident_date': incidentDate,
      },
      timeout: const Duration(seconds: 150),
    ),
  );

  // ---------------------------------------------------------------------
  // Legal research & knowledge base
  // ---------------------------------------------------------------------

  Future<LegalSearchPage> search(
    String query, {
    int limit = 20,
    int offset = 0,
    int? lawId,
    String? jurisdiction,
  }) async {
    final data = await client.get(
      '/api/search',
      query: {
        'q': query,
        'limit': limit,
        'offset': offset,
        'law_id': lawId,
        'jurisdiction': jurisdiction,
      },
    );
    return LegalSearchPage.fromJson(data);
  }

  Future<StatuteSection> section(int sectionId) async =>
      StatuteSection.fromJson(await client.get('/api/sections/$sectionId'));

  Future<Map<String, dynamic>> sectionContext(
    String sectionNumber, {
    String? lawCode,
  }) async => asMap(
    await client.get(
      '/api/knowledge/sections/${Uri.encodeComponent(sectionNumber)}/context',
      query: {if (lawCode != null && lawCode.isNotEmpty) 'law': lawCode},
    ),
  );

  Future<List<LawAct>> acts() async {
    final data = await client.get('/api/knowledge/acts');
    return asMapList(data).map(LawAct.fromJson).toList();
  }

  Future<Map<String, dynamic>> actDetail(int actId) async =>
      asMap(await client.get('/api/knowledge/acts/$actId'));

  Future<List<Map<String, dynamic>>> offences({int? lawId}) async => asMapList(
    await client.get(
      '/api/knowledge/offences',
      query: {if (lawId != null) 'law_id': lawId},
    ),
  );

  Future<List<Map<String, dynamic>>> judgments() async =>
      asMapList(await client.get('/api/knowledge/judgments'));

  Future<KnowledgeOverview> knowledgeOverview() async =>
      KnowledgeOverview.fromJson(await client.get('/api/knowledge/overview'));

  // ---------------------------------------------------------------------
  // Documentation support
  // ---------------------------------------------------------------------

  Future<List<Map<String, dynamic>>> documentationCategories() async =>
      asMapList(await client.get('/api/documentation/categories'));

  Future<Map<String, dynamic>> documentationProcedures({
    String? category,
    String? search,
    int limit = 100,
  }) async => asMap(
    await client.get(
      '/api/documentation/procedures',
      query: {
        if (category != null && category.isNotEmpty) 'category': category,
        if (search != null && search.isNotEmpty) 'search': search,
        'limit': limit,
      },
    ),
  );

  Future<Map<String, dynamic>> documentationProcedure(int procedureId) async =>
      asMap(await client.get('/api/documentation/procedures/$procedureId'));

  // ---------------------------------------------------------------------
  // Document analysis
  // ---------------------------------------------------------------------

  Future<Map<String, dynamic>> analyzeDocumentFile(
    String filePath, {
    String? documentTitle,
    int? caseId,
  }) async => asMap(
    await client.upload(
      '/api/analysis/upload',
      filePath: filePath,
      fields: {
        if (documentTitle != null) 'document_title': documentTitle,
        if (caseId != null) 'case_id': '$caseId',
      },
    ),
  );

  Future<Map<String, dynamic>> analyzeDocumentText({
    required String text,
    String? documentTitle,
    int? caseId,
  }) async => asMap(
    await client.post(
      '/api/analysis/text',
      body: {'text': text, 'document_title': documentTitle, 'case_id': caseId},
    ),
  );

  Future<Map<String, dynamic>> analysisHistory() async =>
      asMap(await client.get('/api/analysis/history'));

  Future<Map<String, dynamic>> analysisDetail(int analysisId) async =>
      asMap(await client.get('/api/analysis/$analysisId'));

  Future<void> deleteAnalysis(int analysisId) async {
    await client.delete('/api/analysis/$analysisId');
  }

  Future<Map<String, dynamic>> saveAnalysisToCase(
    int analysisId,
    Map<String, dynamic> body,
  ) async => asMap(
    await client.post('/api/analysis/$analysisId/save-to-case', body: body),
  );

  // ---------------------------------------------------------------------
  // Legal tools
  // ---------------------------------------------------------------------

  Future<Map<String, dynamic>> evaluateResolution(
    Map<String, dynamic> body,
  ) async => asMap(await client.post('/api/resolution/evaluate', body: body));

  Future<Map<String, dynamic>> analyzeTraffic(
    Map<String, dynamic> body,
  ) async => asMap(await client.post('/api/traffic/analyze', body: body));

  Future<List<Map<String, dynamic>>> trafficOffences() async =>
      asMapList(await client.get('/api/traffic/offences'));

  Future<Map<String, dynamic>> analyzeConstitutional(
    Map<String, dynamic> body,
  ) async =>
      asMap(await client.post('/api/constitutional/analyze', body: body));

  Future<List<Map<String, dynamic>>> constitutionalRights() async {
    final data = asMap(await client.get('/api/constitutional/rights'));
    return asMapList(data['rights']);
  }

  Future<List<Map<String, dynamic>>> authorityDomains() async {
    final data = asMap(await client.get('/api/authority/domains'));
    return asMapList(data['domains']);
  }

  Future<Map<String, dynamic>> recommendAuthorities(String query) async =>
      asMap(
        await client.get(
          '/api/authorities/recommend',
          query: {'q': query, 'limit': 15},
        ),
      );

  Future<List<Map<String, dynamic>>> emergencyHelplines() async {
    final data = asMap(await client.get('/api/emergency/helplines'));
    return asMapList(data['helplines']);
  }

  Future<Map<String, dynamic>> emergencyIntercept(String text) async => asMap(
    await client.post('/api/emergency/intercept', body: {'text': text}),
  );

  Future<Map<String, dynamic>> generateComplaint(
    Map<String, dynamic> body,
  ) async => asMap(
    await client.post(
      '/api/v1/complaint-generator/generate',
      body: body,
      timeout: const Duration(seconds: 90),
    ),
  );

  Future<DownloadResult> exportComplaintDocx(
    Map<String, dynamic> draft,
  ) async => client.postDownload(
    '/api/v1/complaint-generator/export-docx',
    body: {'draft': draft},
    fallbackName: 'Vidhik_Complaint.docx',
  );

  Future<Map<String, dynamic>> recommendStatutoryAuthority(
    Map<String, dynamic> body,
  ) async => asMap(await client.post('/api/authority/recommend', body: body));

  // ---------------------------------------------------------------------
  // Lawyer workspace
  // ---------------------------------------------------------------------

  Future<Map<String, dynamic>> lawyerDashboard() async =>
      asMap(await client.get('/api/lawyer/dashboard'));

  Future<Map<String, dynamic>> lawyerClients({String? search}) async => asMap(
    await client.get(
      '/api/lawyer/clients',
      query: {if (search != null && search.isNotEmpty) 'search': search},
    ),
  );

  Future<Map<String, dynamic>> lawyerClient(int clientId) async =>
      asMap(await client.get('/api/lawyer/clients/$clientId'));

  Future<Map<String, dynamic>> createLawyerClient(
    Map<String, dynamic> body,
  ) async => asMap(await client.post('/api/lawyer/clients', body: body));

  Future<Map<String, dynamic>> lawyerCases({
    String? search,
    String? status,
  }) async => asMap(
    await client.get(
      '/api/lawyer/cases',
      query: {
        if (search != null && search.isNotEmpty) 'search': search,
        if (status != null && status.isNotEmpty) 'status': status,
      },
    ),
  );

  Future<Map<String, dynamic>> lawyerCase(int caseId) async =>
      asMap(await client.get('/api/lawyer/cases/$caseId'));

  Future<Map<String, dynamic>> createLawyerCase(
    Map<String, dynamic> body,
  ) async => asMap(await client.post('/api/lawyer/cases', body: body));

  Future<List<Map<String, dynamic>>> lawyerNotes(int caseId) async =>
      asMapList(await client.get('/api/lawyer/cases/$caseId/notes'));

  Future<Map<String, dynamic>> addLawyerNote(
    int caseId,
    String noteText, {
    String? title,
    bool isPinned = false,
  }) async => asMap(
    await client.post(
      '/api/lawyer/cases/$caseId/notes',
      body: {
        'case_id': caseId,
        'content': noteText,
        'title': title ?? 'Case note',
        'is_pinned': isPinned,
      },
    ),
  );

  Future<Map<String, dynamic>> lawyerDocuments() async =>
      asMap(await client.get('/api/lawyer/documents'));

  Future<Map<String, dynamic>> lawyerHearings() async =>
      asMap(await client.get('/api/lawyer/hearings'));

  Future<Map<String, dynamic>> lawyerProfile() async =>
      asMap(await client.get('/api/lawyer/profile'));

  Future<Map<String, dynamic>> updateLawyerProfile(
    Map<String, dynamic> body,
  ) async => asMap(await client.put('/api/lawyer/profile', body: body));

  Future<List<Map<String, dynamic>>> lawyerDirectory({
    String? search,
    String? city,
    String? specialization,
  }) async {
    final data = await client.get(
      '/api/lawyer/directory',
      query: {
        if (search != null && search.isNotEmpty) 'search': search,
        if (city != null && city.isNotEmpty) 'city': city,
        if (specialization != null && specialization.isNotEmpty)
          'specialization': specialization,
      },
    );
    return asMapList(data);
  }

  Future<Map<String, dynamic>> createHearing(Map<String, dynamic> body) async =>
      asMap(await client.post('/api/lawyer/hearings', body: body));

  // ---------------------------------------------------------------------
  // Video evidence
  // ---------------------------------------------------------------------

  Future<Map<String, dynamic>> uploadEvidence(
    String filePath, {
    String? conversationId,
  }) async => asMap(
    await client.upload(
      '/api/evidence/upload',
      filePath: filePath,
      fields: {if (conversationId != null) 'conversation_id': conversationId},
    ),
  );

  Future<Map<String, dynamic>> evidenceList({
    int limit = 20,
    int offset = 0,
  }) async => asMap(
    await client.get(
      '/api/evidence',
      query: {'limit': limit, 'offset': offset},
    ),
  );

  Future<Map<String, dynamic>> evidenceDetail(int evidenceId) async =>
      asMap(await client.get('/api/evidence/$evidenceId'));

  Future<void> retryEvidence(int evidenceId) async {
    await client.post('/api/evidence/$evidenceId/retry', body: const {});
  }

  Future<DownloadResult> downloadEvidenceReport(int evidenceId) async =>
      client.download(
        '/api/evidence/$evidenceId/download-report',
        fallbackName: 'Vidhik_Evidence_Report_EVD$evidenceId.docx',
      );

  // ---------------------------------------------------------------------
  // Administration
  // ---------------------------------------------------------------------

  Future<Map<String, dynamic>> adminOverview() async =>
      asMap(await client.get('/api/admin/overview'));

  Future<Map<String, dynamic>> adminUsers() async =>
      asMap(await client.get('/api/admin/users'));

  Future<List<Map<String, dynamic>>> adminAuditLogs() async {
    final data = await client.get('/api/admin/audit-logs');
    if (data is Map) {
      final map = asMap(data);
      return asMapList(map['logs'] ?? map['audit_logs'] ?? map['items']);
    }
    return asMapList(data);
  }

  Future<Map<String, dynamic>> health() async =>
      asMap(await client.get('/health'));
}
