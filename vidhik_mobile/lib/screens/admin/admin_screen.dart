import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/format.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';

class AdminScreen extends StatefulWidget {
  const AdminScreen({super.key});

  @override
  State<AdminScreen> createState() => _AdminScreenState();
}

class _AdminScreenState extends State<AdminScreen> {
  late Future<Map<String, dynamic>> _overviewFuture;
  late Future<Map<String, dynamic>> _usersFuture;
  late Future<List<Map<String, dynamic>>> _logsFuture;

  @override
  void initState() {
    super.initState();
    final api = context.read<ApiService>();
    _overviewFuture = api.adminOverview();
    _usersFuture = api.adminUsers();
    _logsFuture = api.adminAuditLogs();
  }

  Future<void> _reload() async {
    final api = context.read<ApiService>();
    setState(() {
      _overviewFuture = api.adminOverview();
      _usersFuture = api.adminUsers();
      _logsFuture = api.adminAuditLogs();
    });
    await Future.wait([_overviewFuture, _usersFuture, _logsFuture]);
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Administration'),
          actions: [
            IconButton(onPressed: _reload, icon: const Icon(Icons.refresh)),
          ],
          bottom: const TabBar(
            labelColor: Colors.white,
            unselectedLabelColor: Colors.white60,
            indicatorColor: AppColors.tealBright,
            tabs: [
              Tab(text: 'Overview'),
              Tab(text: 'Users'),
              Tab(text: 'Audit log'),
            ],
          ),
        ),
        body: TabBarView(children: [_overviewTab(), _usersTab(), _logsTab()]),
      ),
    );
  }

  Widget _overviewTab() {
    return FutureBuilder<Map<String, dynamic>>(
      future: _overviewFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(
            child: CircularProgressIndicator(strokeWidth: 2.4),
          );
        }
        if (snapshot.hasError) {
          return ErrorState(
            message: '${snapshot.error}'.replaceFirst('ApiException: ', ''),
            onRetry: _reload,
          );
        }
        final data = asMap(snapshot.data);
        final metrics = asMap(data['metrics']);
        final environment = asMap(data['environment']);
        return ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
          children: [
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(
                        Icons.admin_panel_settings_outlined,
                        color: AppColors.teal,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        firstNonEmpty([data['status'], 'Platform']),
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 15,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 5),
                  Text(
                    firstNonEmpty([data['security_tier'], '']),
                    style: const TextStyle(
                      fontSize: 11,
                      color: AppColors.muted,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisSpacing: 10,
              mainAxisSpacing: 10,
              childAspectRatio: 1.6,
              children: [
                StatTile(
                  label: 'Total users',
                  value: asInt(metrics['total_users']),
                  icon: Icons.people_outline,
                ),
                StatTile(
                  label: 'Citizens',
                  value: asInt(metrics['citizens']),
                  icon: Icons.person_outline,
                  color: AppColors.info,
                ),
                StatTile(
                  label: 'Lawyers',
                  value: asInt(metrics['lawyers']),
                  icon: Icons.work_outline,
                  color: AppColors.accent,
                ),
                StatTile(
                  label: 'Active cases',
                  value: asInt(metrics['active_cases']),
                  icon: Icons.gavel,
                  color: AppColors.success,
                ),
              ],
            ),
            const SizedBox(height: 16),
            const SectionTitle('Environment'),
            AppCard(
              child: Column(
                children: [
                  InfoRow(
                    'Engine',
                    firstNonEmpty([environment['engine'], '—']),
                  ),
                  InfoRow(
                    'Database',
                    firstNonEmpty([environment['database'], '—']),
                  ),
                  InfoRow(
                    'Statutory coverage',
                    firstNonEmpty([environment['statutory_coverage'], '—']),
                  ),
                  InfoRow(
                    'Administrators',
                    '${asInt(metrics['administrators'])}',
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _usersTab() {
    return FutureBuilder<Map<String, dynamic>>(
      future: _usersFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(
            child: CircularProgressIndicator(strokeWidth: 2.4),
          );
        }
        if (snapshot.hasError) {
          return ErrorState(
            message: '${snapshot.error}'.replaceFirst('ApiException: ', ''),
            onRetry: _reload,
          );
        }
        final data = asMap(snapshot.data);
        final users = asMapList(data['users'] ?? data['items']);
        return ListView(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 28),
          children: [
            Text(
              '${asInt(data['total'], users.length)} registered users',
              style: const TextStyle(fontSize: 12, color: AppColors.muted),
            ),
            const SizedBox(height: 10),
            for (final user in users)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: AppCard(
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 18,
                        backgroundColor: AppColors.navy,
                        child: Text(
                          initialsOf(
                            firstNonEmpty([
                              user['full_name'],
                              user['email'],
                              'U',
                            ]),
                          ),
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              firstNonEmpty([
                                user['full_name'],
                                user['email'],
                                'User',
                              ]),
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                                fontSize: 12.5,
                              ),
                            ),
                            Text(
                              [
                                asString(user['email']),
                                asString(user['role']),
                              ].where((e) => e.isNotEmpty).join(' · '),
                              style: const TextStyle(
                                fontSize: 10.5,
                                color: AppColors.muted,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Tag(
                        asBool(user['is_active'], true) ? 'Active' : 'Disabled',
                        color: asBool(user['is_active'], true)
                            ? AppColors.success
                            : AppColors.danger,
                      ),
                    ],
                  ),
                ),
              ),
          ],
        );
      },
    );
  }

  Widget _logsTab() {
    return FutureBuilder<List<Map<String, dynamic>>>(
      future: _logsFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(
            child: CircularProgressIndicator(strokeWidth: 2.4),
          );
        }
        if (snapshot.hasError) {
          return ErrorState(
            message: '${snapshot.error}'.replaceFirst('ApiException: ', ''),
            onRetry: _reload,
          );
        }
        final logs = snapshot.data ?? const [];
        if (logs.isEmpty) {
          return const EmptyState(
            title: 'No audit events',
            message: 'Security and access events will be recorded here.',
            icon: Icons.receipt_long_outlined,
          );
        }
        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 28),
          itemCount: logs.length,
          separatorBuilder: (_, __) => const SizedBox(height: 8),
          itemBuilder: (context, index) {
            final log = logs[index];
            return AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          firstNonEmpty([
                            log['action'],
                            log['event_type'],
                            'Event',
                          ]),
                          style: const TextStyle(
                            fontWeight: FontWeight.w600,
                            fontSize: 12.5,
                          ),
                        ),
                      ),
                      Text(
                        formatDateTime(log['created_at'] ?? log['timestamp']),
                        style: const TextStyle(
                          fontSize: 10,
                          color: AppColors.muted,
                        ),
                      ),
                    ],
                  ),
                  if (asString(log['description']).isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      asString(log['description']),
                      style: const TextStyle(fontSize: 11.5, height: 1.4),
                    ),
                  ],
                  if (asString(log['ip_address']).isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      'IP ${log['ip_address']}',
                      style: const TextStyle(
                        fontSize: 10,
                        color: AppColors.muted,
                      ),
                    ),
                  ],
                ],
              ),
            );
          },
        );
      },
    );
  }
}
