import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/format.dart';
import '../../models/citizen.dart';
import '../../providers/auth_provider.dart';
import '../../providers/settings_provider.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';
import '../assistant/assistant_screen.dart';
import '../cases/case_intelligence_screen.dart';
import '../cases/citizen_cases_screen.dart';
import '../documents/document_analysis_screen.dart';
import '../lawyers/find_lawyer_screen.dart';
import '../notifications/notifications_screen.dart';
import '../research/research_screen.dart';

class CitizenDashboardScreen extends StatefulWidget {
  const CitizenDashboardScreen({super.key, this.onNavigateTab});

  /// Allows the dashboard to switch the shell's bottom navigation tab.
  final ValueChanged<int>? onNavigateTab;

  @override
  State<CitizenDashboardScreen> createState() => _CitizenDashboardScreenState();
}

class _CitizenDashboardScreenState extends State<CitizenDashboardScreen> {
  late Future<CitizenDashboard> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().citizenDashboard();
  }

  Future<void> _reload() async {
    setState(() {
      _future = context.read<ApiService>().citizenDashboard();
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final settings = context.watch<SettingsProvider>();
    final name = auth.user?.safeName ?? 'Citizen';

    return RefreshIndicator(
      onRefresh: _reload,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
        children: [
          _welcomeCard(
            name,
            auth.user?.displayRole ?? 'Citizen',
            settings.languageLabel,
          ),
          const SizedBox(height: 16),
          AsyncView<CitizenDashboard>(
            future: _future,
            onRetry: _reload,
            loadingText: 'Loading your legal workspace…',
            builder: (context, data) => Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                GridView.count(
                  crossAxisCount: 3,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  crossAxisSpacing: 10,
                  mainAxisSpacing: 10,
                  childAspectRatio: 0.92,
                  children: [
                    StatTile(
                      label: 'Active cases',
                      value: data.activeCases,
                      icon: Icons.gavel_rounded,
                    ),
                    StatTile(
                      label: 'Documents',
                      value: data.documentsCount,
                      icon: Icons.folder_copy_outlined,
                      color: AppColors.info,
                    ),
                    StatTile(
                      label: 'Hearings',
                      value: data.upcomingHearingsCount,
                      icon: Icons.event_outlined,
                      color: AppColors.accent,
                    ),
                    StatTile(
                      label: 'Alerts',
                      value: data.unreadNotificationsCount,
                      icon: Icons.notifications_active_outlined,
                      color: AppColors.danger,
                    ),
                    StatTile(
                      label: 'Saved sections',
                      value: data.savedSectionsCount,
                      icon: Icons.bookmark_outline,
                      color: AppColors.success,
                    ),
                    StatTile(
                      label: 'Procedures',
                      value: data.trackedProceduresCount,
                      icon: Icons.checklist_rtl,
                      color: AppColors.teal,
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                _assistantHero(context),
                const SizedBox(height: 20),
                const SectionTitle('Quick actions'),
                GridView.count(
                  crossAxisCount: 2,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  crossAxisSpacing: 10,
                  mainAxisSpacing: 10,
                  childAspectRatio: 1.68,
                  children: [
                    ActionTile(
                      icon: Icons.search,
                      title: 'Legal research',
                      subtitle: 'Search BNS, BNSS, BSA & 24 Acts',
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => const ResearchScreen(),
                        ),
                      ),
                    ),
                    ActionTile(
                      icon: Icons.psychology_alt_outlined,
                      title: 'Case intelligence',
                      subtitle: 'Analyse your situation',
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => const CaseIntelligenceScreen(),
                        ),
                      ),
                    ),
                    ActionTile(
                      icon: Icons.article_outlined,
                      title: 'Document analysis',
                      subtitle: 'Review contracts & notices',
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => const DocumentAnalysisScreen(),
                        ),
                      ),
                    ),
                    ActionTile(
                      icon: Icons.support_agent,
                      title: 'Find a lawyer',
                      subtitle: 'Verified advocates directory',
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => const LawyerDirectoryScreen(),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                SectionTitle(
                  'Recent cases',
                  action: TextButton(
                    onPressed: () => widget.onNavigateTab?.call(2),
                    child: const Text('View all'),
                  ),
                ),
                if (data.recentCases.isEmpty)
                  const AppCard(
                    child: EmptyState(
                      title: 'No cases yet',
                      message: 'Register a matter or describe your situation to Case Intelligence to get started.',
                      icon: Icons.folder_open_outlined,
                    ),
                  )
                else
                  for (final item in data.recentCases.take(4))
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: _recentCaseTile(context, item),
                    ),
                const SizedBox(height: 14),
                SectionTitle(
                  'Upcoming hearings',
                  action: TextButton(
                    onPressed: () => widget.onNavigateTab?.call(2),
                    child: const Text('Cases'),
                  ),
                ),
                if (data.upcomingHearings.isEmpty)
                  const AppCard(
                    child: Padding(
                      padding: EdgeInsets.symmetric(vertical: 14),
                      child: Text(
                        'No upcoming hearings on record.',
                        style: TextStyle(color: AppColors.muted),
                      ),
                    ),
                  )
                else
                  for (final hearing in data.upcomingHearings.take(3))
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: _hearingTile(hearing),
                    ),
                const SizedBox(height: 14),
                SectionTitle(
                  'Notifications',
                  action: TextButton(
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => const NotificationsScreen(),
                      ),
                    ),
                    child: const Text('Open'),
                  ),
                ),
                if (data.recentNotifications.isEmpty)
                  const AppCard(
                    child: Padding(
                      padding: EdgeInsets.symmetric(vertical: 14),
                      child: Text(
                        'No notifications yet.',
                        style: TextStyle(color: AppColors.muted),
                      ),
                    ),
                  )
                else
                  for (final notification in data.recentNotifications.take(3))
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: AppCard(
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(
                              notification['is_read'] == true
                                  ? Icons.notifications_none
                                  : Icons.notifications_active,
                              size: 18,
                              color: notification['is_read'] == true
                                  ? AppColors.muted
                                  : AppColors.teal,
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    firstNonEmpty([
                                      notification['title'],
                                      'Notification',
                                    ]),
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w600,
                                      fontSize: 13,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    asString(notification['message']),
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      fontSize: 12,
                                      color: AppColors.muted,
                                      height: 1.35,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                const SizedBox(height: 18),
                _disclaimerCard(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _welcomeCard(String name, String role, String language) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppColors.navy, Color(0xFF145C66)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 21,
                backgroundColor: Colors.white.withValues(alpha: 0.12),
                child: Text(
                  initialsOf(name),
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Welcome, $name',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '$role workspace · $language',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.72),
                        fontSize: 11.5,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.tealBright.withValues(alpha: 0.28),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: const Text(
                  'SECURE',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 9.5,
                    letterSpacing: 0.8,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Your legal matters, documents and AI guidance in one place.',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.82),
              fontSize: 12.5,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }

  Widget _assistantHero(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.navy,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.auto_awesome, color: AppColors.tealBright, size: 20),
              SizedBox(width: 8),
              Text(
                'Vidhik AI Legal Assistant',
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                  fontSize: 15,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Grounded answers with traceable citations from the Indian statutory corpus — no invented law.',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.78),
              fontSize: 12,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.tealBright,
              ),
              onPressed: () {
                if (widget.onNavigateTab != null) {
                  widget.onNavigateTab!(1);
                } else {
                  Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const AssistantScreen()),
                  );
                }
              },
              icon: const Icon(Icons.chat_bubble_outline, size: 18),
              label: const Text('Ask a legal question'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _recentCaseTile(BuildContext context, Map<String, dynamic> item) {
    final caseId = asInt(item['case_id'] ?? item['id']);
    final title = firstNonEmpty([item['case_title'], item['title'], 'Matter']);
    final status = firstNonEmpty([item['status'], 'active']);
    return AppCard(
      onTap: caseId <= 0
          ? null
          : () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => CitizenCaseDetailScreen(caseId: caseId),
              ),
            ),
      padding: const EdgeInsets.all(13),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(9),
            decoration: BoxDecoration(
              color: AppColors.teal.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.gavel, size: 18, color: AppColors.teal),
          ),
          const SizedBox(width: 11),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 13.5,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  [
                    if (asString(item['case_type']).isNotEmpty)
                      asString(item['case_type']),
                    if (asString(item['court_name']).isNotEmpty)
                      asString(item['court_name']),
                    status,
                  ].join(' · '),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 11.5,
                    color: AppColors.muted,
                  ),
                ),
              ],
            ),
          ),
          const Icon(Icons.chevron_right, color: AppColors.muted),
        ],
      ),
    );
  }

  Widget _hearingTile(Map<String, dynamic> hearing) {
    return AppCard(
      padding: const EdgeInsets.all(13),
      child: Row(
        children: [
          const Icon(Icons.event, size: 18, color: AppColors.accent),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  firstNonEmpty([
                    hearing['case_title'],
                    hearing['title'],
                    'Hearing',
                  ]),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  [
                    formatDate(hearing['hearing_date'] ?? hearing['date']),
                    if (asString(hearing['courtroom']).isNotEmpty)
                      'Courtroom ${hearing['courtroom']}',
                    if (asString(hearing['purpose']).isNotEmpty)
                      asString(hearing['purpose']),
                  ].join(' · '),
                  style: const TextStyle(
                    fontSize: 11.5,
                    color: AppColors.muted,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _disclaimerCard() {
    return Container(
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: AppColors.warning.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.warning.withValues(alpha: 0.2)),
      ),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline, size: 16, color: AppColors.warning),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              'VIDHIK AI provides legal awareness and research support grounded in Indian statutes. '
              'It is not legal advice and does not create a lawyer-client relationship.',
              style: TextStyle(
                fontSize: 11,
                color: AppColors.muted,
                height: 1.45,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
