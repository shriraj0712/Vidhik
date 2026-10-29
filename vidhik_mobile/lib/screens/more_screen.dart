import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/theme/app_theme.dart';
import '../core/utils/format.dart';
import '../providers/auth_provider.dart';
import '../widgets/common.dart';
import 'admin/admin_screen.dart';
import 'citizen/bookmarks_screen.dart';
import 'citizen/search_history_screen.dart';
import 'courts/case_tracking_screen.dart';
import 'documentation/documentation_screen.dart';
import 'documents/document_analysis_screen.dart';
import 'evidence/evidence_screen.dart';
import 'knowledge/knowledge_base_screen.dart';
import 'lawyer/lawyer_workspace_screen.dart';
import 'lawyers/find_lawyer_screen.dart';
import 'notifications/notifications_screen.dart';
import 'profile/profile_screen.dart';
import 'security/security_screen.dart';
import 'settings/settings_screen.dart';
import 'tools/legal_tools_screens.dart';

/// Hub for everything that does not fit the four primary destinations.
class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  void _open(BuildContext context, Widget screen) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final user = auth.user;
    final isLawyer = user?.isLawyer ?? false;
    final isAdmin = user?.isAdmin ?? false;

    return Scaffold(
      appBar: AppBar(title: const Text('More')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
        children: [
          AppCard(
            onTap: () => _open(context, const ProfileScreen()),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 24,
                  backgroundColor: AppColors.navy,
                  child: Text(
                    initialsOf(user?.safeName ?? 'Vidhik'),
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                      fontSize: 15,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        user?.safeName ?? 'Vidhik user',
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 15,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        [
                          user?.displayRole ?? 'Citizen',
                          asString(user?.email),
                        ].where((e) => e.isNotEmpty).join(' · '),
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
          ),
          const SizedBox(height: 18),
          const SectionTitle('Account'),
          _group([
            _Entry(
              Icons.bookmark_border,
              'Bookmarks',
              'Saved statutory provisions',
              () => _open(context, const BookmarksScreen()),
            ),
            _Entry(
              Icons.history,
              'Search history',
              'Your previous legal research queries',
              () => _open(context, const SearchHistoryScreen()),
            ),
            _Entry(
              Icons.notifications_none,
              'Notifications',
              'Case updates and hearing reminders',
              () => _open(context, const NotificationsScreen()),
            ),
            _Entry(
              Icons.shield_outlined,
              'Security & sessions',
              'Two-factor authentication and devices',
              () => _open(context, const SecurityScreen()),
            ),
            _Entry(
              Icons.tune,
              'Settings',
              'Language, theme and preferences',
              () => _open(context, const SettingsScreen()),
            ),
          ]),
          if (!isLawyer && !isAdmin) ...[
            const SizedBox(height: 18),
            const SectionTitle('Legal services'),
            _group([
              _Entry(
                Icons.track_changes,
                'Case tracking',
                'Track matters by CNR or filing number',
                () => _open(context, const CaseTrackingScreen()),
              ),
              _Entry(
                Icons.menu_book_outlined,
                'Knowledge base',
                'Acts, offences and landmark judgments',
                () => _open(context, const KnowledgeBaseScreen()),
              ),
              _Entry(
                Icons.directions_walk,
                'Know your rights',
                'Constitutional protections in plain language',
                () => _open(context, const ConstitutionalRightsScreen()),
              ),
              _Entry(
                Icons.local_police_outlined,
                'Emergency help',
                'Helplines and immediate response guidance',
                () => _open(context, const EmergencyScreen()),
              ),
              _Entry(
                Icons.work_outline,
                'Find a lawyer',
                'Browse verified advocates by expertise',
                () => _open(context, const LawyerDirectoryScreen()),
              ),
            ]),
            const SizedBox(height: 18),
            const SectionTitle('Tools'),
            _group([
              _Entry(
                Icons.description_outlined,
                'Document analysis',
                'Understand notices, agreements and orders',
                () => _open(context, const DocumentAnalysisScreen()),
              ),
              _Entry(
                Icons.video_library_outlined,
                'Evidence vault',
                'Upload and analyse audio-video evidence',
                () => _open(context, const EvidenceScreen()),
              ),
              _Entry(
                Icons.calculate_outlined,
                'Legal tools',
                'Traffic law, resolution and authority finder',
                () => _showTools(context),
              ),
              _Entry(
                Icons.assignment_outlined,
                'Complaint generator',
                'Draft a formal complaint from case facts',
                () => _open(context, const ComplaintGeneratorScreen()),
              ),
              _Entry(
                Icons.library_books_outlined,
                'Procedures',
                'Step-by-step documentation guidance',
                () => _open(context, const DocumentationScreen()),
              ),
            ]),
          ],
          if (isLawyer) ...[
            const SizedBox(height: 18),
            const SectionTitle('Practice'),
            _group([
              _Entry(
                Icons.dashboard_outlined,
                'Advocate workspace',
                'Clients, matters, notes and hearings',
                () => _open(context, const LawyerWorkspaceScreen()),
              ),
              _Entry(
                Icons.people_outline,
                'Lawyer directory',
                'Peer directory of verified advocates',
                () => _open(context, const LawyerDirectoryScreen()),
              ),
              _Entry(
                Icons.menu_book_outlined,
                'Knowledge base',
                'Acts, offences and judgments',
                () => _open(context, const KnowledgeBaseScreen()),
              ),
              _Entry(
                Icons.description_outlined,
                'Document analysis',
                'Analyse client files and orders',
                () => _open(context, const DocumentAnalysisScreen()),
              ),
            ]),
          ],
          if (isAdmin) ...[
            const SizedBox(height: 18),
            const SectionTitle('Administration'),
            _group([
              _Entry(
                Icons.admin_panel_settings_outlined,
                'Admin console',
                'Platform metrics, users and audit trail',
                () => _open(context, const AdminScreen()),
              ),
              _Entry(
                Icons.menu_book_outlined,
                'Knowledge base',
                'Statutory corpus management view',
                () => _open(context, const KnowledgeBaseScreen()),
              ),
            ]),
          ],
          const SizedBox(height: 22),
          OutlinedButton.icon(
            onPressed: () => showLicensePage(
              context: context,
              applicationName: 'VIDHIK AI',
              applicationVersion: '1.0.0',
            ),
            icon: const Icon(Icons.info_outline, size: 18),
            label: const Text('About VIDHIK'),
          ),
          const SizedBox(height: 14),
          const Text(
            'VIDHIK provides legal information and decision support. It is not a '
            'substitute for advice from a qualified advocate.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 11, color: AppColors.muted, height: 1.5),
          ),
        ],
      ),
    );
  }

  Widget _group(List<_Entry> entries) {
    return AppCard(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Column(
        children: [
          for (var i = 0; i < entries.length; i++) ...[
            ListTile(
              dense: true,
              leading: Icon(entries[i].icon, size: 21, color: AppColors.teal),
              title: Text(
                entries[i].title,
                style: const TextStyle(
                  fontSize: 13.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
              subtitle: Text(
                entries[i].subtitle,
                style: const TextStyle(fontSize: 11, color: AppColors.muted),
              ),
              trailing: const Icon(
                Icons.chevron_right,
                size: 18,
                color: AppColors.muted,
              ),
              onTap: entries[i].onTap,
            ),
            if (i != entries.length - 1)
              const Divider(height: 1, indent: 54, endIndent: 16),
          ],
        ],
      ),
    );
  }

  void _showTools(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) {
        void openFromSheet(Widget screen) {
          Navigator.pop(sheetContext);
          _open(context, screen);
        }

        final tools = [
          _Entry(
            Icons.balance,
            'Dispute resolution',
            'Evaluate settlement options',
            () => openFromSheet(const ResolutionScreen()),
          ),
          _Entry(
            Icons.directions_car,
            'Traffic law',
            'Analyse a traffic violation',
            () => openFromSheet(const TrafficLawScreen()),
          ),
          _Entry(
            Icons.account_balance_outlined,
            'Authority finder',
            'Find the right forum and filing channel',
            () => openFromSheet(const AuthorityFinderScreen()),
          ),
        ];
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Padding(
                padding: EdgeInsets.only(bottom: 6),
                child: Text(
                  'Legal tools',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
                ),
              ),
              for (final tool in tools)
                ListTile(
                  leading: Icon(tool.icon, color: AppColors.teal),
                  title: Text(tool.title),
                  subtitle: Text(tool.subtitle),
                  trailing: const Icon(Icons.chevron_right, size: 18),
                  onTap: tool.onTap,
                ),
              const SizedBox(height: 10),
            ],
          ),
        );
      },
    );
  }
}

class _Entry {
  const _Entry(this.icon, this.title, this.subtitle, this.onTap);

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;
}
