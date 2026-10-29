import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/format.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';

class LawyerWorkspaceScreen extends StatefulWidget {
  const LawyerWorkspaceScreen({super.key, this.initialTab = 0});

  final int initialTab;

  @override
  State<LawyerWorkspaceScreen> createState() => _LawyerWorkspaceScreenState();
}

class _LawyerWorkspaceScreenState extends State<LawyerWorkspaceScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(
      length: 6,
      vsync: this,
      initialIndex: widget.initialTab.clamp(0, 5),
    );
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthProvider>().user;
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Advocate workspace'),
            Text(
              user?.safeName ?? '',
              style: const TextStyle(fontSize: 10.5, color: Colors.white70),
            ),
          ],
        ),
        bottom: TabBar(
          controller: _tabs,
          isScrollable: true,
          tabAlignment: TabAlignment.start,
          labelColor: Colors.white,
          unselectedLabelColor: Colors.white60,
          indicatorColor: AppColors.tealBright,
          tabs: const [
            Tab(text: 'Dashboard'),
            Tab(text: 'Cases'),
            Tab(text: 'Clients'),
            Tab(text: 'Hearings'),
            Tab(text: 'Documents'),
            Tab(text: 'Profile'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabs,
        children: const [
          _LawyerDashboardTab(),
          _LawyerCasesTab(),
          _LawyerClientsTab(),
          _LawyerHearingsTab(),
          _LawyerDocumentsTab(),
          _LawyerProfileTab(),
        ],
      ),
    );
  }
}

class _LawyerDashboardTab extends StatefulWidget {
  const _LawyerDashboardTab();

  @override
  State<_LawyerDashboardTab> createState() => _LawyerDashboardTabState();
}

class _LawyerDashboardTabState extends State<_LawyerDashboardTab> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().lawyerDashboard();
  }

  Future<void> _reload() async {
    setState(() {
      _future = context.read<ApiService>().lawyerDashboard();
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _reload,
      child: AsyncView<Map<String, dynamic>>(
        future: _future,
        onRetry: _reload,
        loadingText: 'Loading your practice…',
        builder: (context, data) {
          final recentCases = asMapList(data['recent_cases']);
          final hearings = asMapList(data['upcoming_hearings_list']);
          final documents = asMapList(data['recent_documents']);
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
            children: [
              GridView.count(
                crossAxisCount: 2,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisSpacing: 10,
                mainAxisSpacing: 10,
                childAspectRatio: 1.55,
                children: [
                  StatTile(
                    label: 'Total clients',
                    value: asInt(data['total_clients']),
                    icon: Icons.people_outline,
                  ),
                  StatTile(
                    label: 'Active cases',
                    value: asInt(data['active_cases']),
                    icon: Icons.gavel,
                    color: AppColors.info,
                  ),
                  StatTile(
                    label: 'Upcoming hearings',
                    value: asInt(data['upcoming_hearings']),
                    icon: Icons.event,
                    color: AppColors.accent,
                  ),
                  StatTile(
                    label: 'Recent documents',
                    value: asInt(data['recent_documents_count']),
                    icon: Icons.folder_copy_outlined,
                    color: AppColors.success,
                  ),
                ],
              ),
              const SizedBox(height: 18),
              const SectionTitle('Recent cases'),
              if (recentCases.isEmpty)
                const AppCard(
                  child: Text(
                    'No cases yet.',
                    style: TextStyle(color: AppColors.muted),
                  ),
                )
              else
                for (final item in recentCases.take(5))
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: AppCard(
                      child: Row(
                        children: [
                          const Icon(
                            Icons.gavel,
                            size: 17,
                            color: AppColors.teal,
                          ),
                          const SizedBox(width: 9),
                          Expanded(
                            child: Text(
                              firstNonEmpty([item['case_title'], 'Matter']),
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                                fontSize: 13,
                              ),
                            ),
                          ),
                          Tag(firstNonEmpty([item['status'], 'active'])),
                        ],
                      ),
                    ),
                  ),
              const SizedBox(height: 16),
              const SectionTitle('Upcoming hearings'),
              if (hearings.isEmpty)
                const AppCard(
                  child: Text(
                    'No hearings scheduled.',
                    style: TextStyle(color: AppColors.muted),
                  ),
                )
              else
                for (final hearing in hearings.take(5))
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: AppCard(
                      child: Row(
                        children: [
                          const Icon(
                            Icons.event,
                            size: 17,
                            color: AppColors.accent,
                          ),
                          const SizedBox(width: 9),
                          Expanded(
                            child: Text(
                              firstNonEmpty([hearing['title'], 'Hearing']),
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                                fontSize: 13,
                              ),
                            ),
                          ),
                          Text(
                            formatDate(hearing['reminder_date']),
                            style: const TextStyle(
                              fontSize: 11,
                              color: AppColors.muted,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              const SizedBox(height: 16),
              const SectionTitle('Recent documents'),
              if (documents.isEmpty)
                const AppCard(
                  child: Text(
                    'No documents catalogued.',
                    style: TextStyle(color: AppColors.muted),
                  ),
                )
              else
                for (final document in documents.take(4))
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: AppCard(
                      child: Row(
                        children: [
                          const Icon(
                            Icons.description_outlined,
                            size: 17,
                            color: AppColors.info,
                          ),
                          const SizedBox(width: 9),
                          Expanded(
                            child: Text(
                              firstNonEmpty([
                                document['document_name'],
                                'Document',
                              ]),
                              style: const TextStyle(fontSize: 13),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
            ],
          );
        },
      ),
    );
  }
}

class _LawyerCasesTab extends StatefulWidget {
  const _LawyerCasesTab();

  @override
  State<_LawyerCasesTab> createState() => _LawyerCasesTabState();
}

class _LawyerCasesTabState extends State<_LawyerCasesTab> {
  late Future<Map<String, dynamic>> _future;
  String _search = '';

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().lawyerCases();
  }

  void _reload() {
    setState(() {
      _future = context.read<ApiService>().lawyerCases(
        search: _search.isEmpty ? null : _search,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 6),
          child: TextField(
            textInputAction: TextInputAction.search,
            onSubmitted: (value) {
              _search = value.trim();
              _reload();
            },
            decoration: InputDecoration(
              hintText: 'Search cases by title, client or court',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: IconButton(
                onPressed: _reload,
                icon: const Icon(Icons.arrow_forward),
              ),
              isDense: true,
            ),
          ),
        ),
        Expanded(
          child: FutureBuilder<Map<String, dynamic>>(
            future: _future,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Center(
                  child: CircularProgressIndicator(strokeWidth: 2.4),
                );
              }
              if (snapshot.hasError) {
                return ErrorState(
                  message: '${snapshot.error}'.replaceFirst(
                    'ApiException: ',
                    '',
                  ),
                  onRetry: _reload,
                );
              }
              final cases = asMapList(asMap(snapshot.data)['cases']);
              if (cases.isEmpty) {
                return const EmptyState(
                  title: 'No cases',
                  message: 'Cases assigned to your practice will appear here.',
                  icon: Icons.folder_open_outlined,
                );
              }
              return ListView.separated(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 28),
                itemCount: cases.length,
                separatorBuilder: (_, __) => const SizedBox(height: 8),
                itemBuilder: (context, index) {
                  final item = cases[index];
                  return AppCard(
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => LawyerCaseDetailScreen(
                          caseId: asInt(item['case_id']),
                        ),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                firstNonEmpty([item['case_title'], 'Matter']),
                                style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                  fontSize: 13.5,
                                ),
                              ),
                            ),
                            Tag(firstNonEmpty([item['status'], 'active'])),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          [
                            if (asString(item['client_name']).isNotEmpty)
                              asString(item['client_name']),
                            if (asString(item['court_name']).isNotEmpty)
                              asString(item['court_name']),
                            if (asString(item['case_number']).isNotEmpty)
                              'No. ${item['case_number']}',
                          ].join(' · '),
                          style: const TextStyle(
                            fontSize: 11.5,
                            color: AppColors.muted,
                          ),
                        ),
                      ],
                    ),
                  );
                },
              );
            },
          ),
        ),
      ],
    );
  }
}

class _LawyerClientsTab extends StatefulWidget {
  const _LawyerClientsTab();

  @override
  State<_LawyerClientsTab> createState() => _LawyerClientsTabState();
}

class _LawyerClientsTabState extends State<_LawyerClientsTab> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().lawyerClients();
  }

  Future<void> _reload() async {
    setState(() {
      _future = context.read<ApiService>().lawyerClients();
    });
    await _future;
  }

  Future<void> _addClient() async {
    final name = TextEditingController();
    final email = TextEditingController();
    final phone = TextEditingController();
    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        decoration: BoxDecoration(
          color: Theme.of(context).scaffoldBackgroundColor,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(22)),
        ),
        child: SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'Add client',
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: name,
                  textCapitalization: TextCapitalization.words,
                  decoration: const InputDecoration(labelText: 'Full name'),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: email,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(labelText: 'Email'),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: phone,
                  keyboardType: TextInputType.phone,
                  decoration: const InputDecoration(labelText: 'Phone'),
                ),
                const SizedBox(height: 14),
                FilledButton(
                  onPressed: () async {
                    if (name.text.trim().length < 2 ||
                        !email.text.contains('@')) {
                      showErrorSnack(
                        context,
                        'A name and valid email are required.',
                      );
                      return;
                    }
                    try {
                      await context.read<ApiService>().createLawyerClient({
                        'full_name': name.text.trim(),
                        'email': email.text.trim(),
                        'phone': phone.text.trim().isEmpty
                            ? null
                            : phone.text.trim(),
                      });
                      if (context.mounted) Navigator.pop(context, true);
                    } on Exception catch (e) {
                      if (context.mounted) showErrorSnack(context, e);
                    }
                  },
                  child: const Text('Create client'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
    if (saved == true) _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton.small(
        onPressed: _addClient,
        backgroundColor: AppColors.teal,
        foregroundColor: Colors.white,
        child: const Icon(Icons.person_add_alt),
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _future,
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
          final clients = asMapList(asMap(snapshot.data)['clients']);
          if (clients.isEmpty) {
            return const EmptyState(
              title: 'No clients',
              message: 'Add client profiles to link them to active matters.',
              icon: Icons.people_outline,
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 28),
            itemCount: clients.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (context, index) {
              final client = clients[index];
              return AppCard(
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 19,
                      backgroundColor: AppColors.navy,
                      child: Text(
                        initialsOf(firstNonEmpty([client['full_name'], 'C'])),
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    const SizedBox(width: 11),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            firstNonEmpty([client['full_name'], 'Client']),
                            style: const TextStyle(
                              fontWeight: FontWeight.w600,
                              fontSize: 13,
                            ),
                          ),
                          Text(
                            [
                              asString(client['email']),
                              asString(client['phone']),
                            ].where((e) => e.isNotEmpty).join(' · '),
                            style: const TextStyle(
                              fontSize: 11,
                              color: AppColors.muted,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Tag('${asInt(client['active_cases_count'])} active'),
                  ],
                ),
              );
            },
          );
        },
      ),
    );
  }
}

class _LawyerHearingsTab extends StatefulWidget {
  const _LawyerHearingsTab();

  @override
  State<_LawyerHearingsTab> createState() => _LawyerHearingsTabState();
}

class _LawyerHearingsTabState extends State<_LawyerHearingsTab> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().lawyerHearings();
  }

  Future<void> _reload() async {
    setState(() {
      _future = context.read<ApiService>().lawyerHearings();
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Map<String, dynamic>>(
      future: _future,
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
        final upcoming = asMapList(data['upcoming']);
        final past = asMapList(data['past']);
        return RefreshIndicator(
          onRefresh: _reload,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 28),
            children: [
              SectionTitle('Upcoming (${upcoming.length})'),
              if (upcoming.isEmpty)
                const AppCard(
                  child: Text(
                    'No upcoming hearings.',
                    style: TextStyle(color: AppColors.muted),
                  ),
                )
              else
                for (final hearing in upcoming)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: AppCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            firstNonEmpty([hearing['title'], 'Hearing']),
                            style: const TextStyle(
                              fontWeight: FontWeight.w600,
                              fontSize: 13,
                            ),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            [
                              formatDate(hearing['reminder_date']),
                              firstNonEmpty([hearing['case_title'], '']),
                              firstNonEmpty([hearing['court_name'], '']),
                            ].where((e) => e.isNotEmpty).join(' · '),
                            style: const TextStyle(
                              fontSize: 11.5,
                              color: AppColors.muted,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              const SizedBox(height: 16),
              SectionTitle('Past (${past.length})'),
              if (past.isEmpty)
                const AppCard(
                  child: Text(
                    'No past hearings.',
                    style: TextStyle(color: AppColors.muted),
                  ),
                )
              else
                for (final hearing in past.take(15))
                  Padding(
                    padding: const EdgeInsets.only(bottom: 7),
                    child: AppCard(
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              firstNonEmpty([hearing['title'], 'Hearing']),
                              style: const TextStyle(fontSize: 12.5),
                            ),
                          ),
                          Text(
                            formatDate(hearing['reminder_date']),
                            style: const TextStyle(
                              fontSize: 11,
                              color: AppColors.muted,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
            ],
          ),
        );
      },
    );
  }
}

class _LawyerDocumentsTab extends StatefulWidget {
  const _LawyerDocumentsTab();

  @override
  State<_LawyerDocumentsTab> createState() => _LawyerDocumentsTabState();
}

class _LawyerDocumentsTabState extends State<_LawyerDocumentsTab> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().lawyerDocuments();
  }

  Future<void> _reload() async {
    setState(() {
      _future = context.read<ApiService>().lawyerDocuments();
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Map<String, dynamic>>(
      future: _future,
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
        final documents = asMapList(asMap(snapshot.data)['documents']);
        if (documents.isEmpty) {
          return const EmptyState(
            title: 'No case documents',
            message: 'Documents catalogued against your matters appear here. Analyzed documents can be saved to a case from Document Analysis.',
            icon: Icons.folder_copy_outlined,
          );
        }
        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 28),
          itemCount: documents.length,
          separatorBuilder: (_, __) => const SizedBox(height: 8),
          itemBuilder: (context, index) {
            final doc = documents[index];
            return AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    firstNonEmpty([doc['document_name'], 'Document']),
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    [
                      firstNonEmpty([doc['document_type'], 'General']),
                      firstNonEmpty([doc['case_title'], '']),
                      firstNonEmpty([doc['client_name'], '']),
                    ].where((e) => e.isNotEmpty).join(' · '),
                    style: const TextStyle(
                      fontSize: 11.5,
                      color: AppColors.muted,
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }
}

class _LawyerProfileTab extends StatefulWidget {
  const _LawyerProfileTab();

  @override
  State<_LawyerProfileTab> createState() => _LawyerProfileTabState();
}

class _LawyerProfileTabState extends State<_LawyerProfileTab> {
  late Future<Map<String, dynamic>> _future;
  final _bio = TextEditingController();
  final _court = TextEditingController();
  final _office = TextEditingController();
  final _city = TextEditingController();
  bool _filled = false;

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().lawyerProfile();
    _future
        .then((data) {
          if (!mounted) return;
          setState(() {
            _bio.text = asString(data['bio']);
            _court.text = asString(data['court_practice']);
            _office.text = asString(data['office_address']);
            _city.text = asString(data['city']);
            _filled = true;
          });
        })
        .catchError((_) {});
  }

  @override
  void dispose() {
    _bio.dispose();
    _court.dispose();
    _office.dispose();
    _city.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    try {
      await context.read<ApiService>().updateLawyerProfile({
        'bio': _bio.text.trim(),
        'court_practice': _court.text.trim(),
        'office_address': _office.text.trim(),
        'city': _city.text.trim(),
      });
      if (mounted) showInfoSnack(context, 'Professional profile updated.');
    } on Exception catch (e) {
      if (mounted) showErrorSnack(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Map<String, dynamic>>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(
            child: CircularProgressIndicator(strokeWidth: 2.4),
          );
        }
        if (snapshot.hasError) {
          return ErrorState(
            message: '${snapshot.error}'.replaceFirst('ApiException: ', ''),
            onRetry: () => setState(() {
              _future = context.read<ApiService>().lawyerProfile();
            }),
          );
        }
        final data = asMap(snapshot.data);
        return ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
          children: [
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    firstNonEmpty([data['full_name'], 'Advocate']),
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    [
                      firstNonEmpty([
                        data['bar_council_number'],
                        'Bar Council not set',
                      ]),
                      if (asInt(data['experience_years']) > 0)
                        '${data['experience_years']} years',
                    ].join(' · '),
                    style: const TextStyle(
                      fontSize: 11.5,
                      color: AppColors.muted,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Tag(
                    asBool(data['is_verified'], true)
                        ? 'Verified advocate'
                        : 'Pending verification',
                    color: asBool(data['is_verified'], true)
                        ? AppColors.success
                        : AppColors.warning,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            const SectionTitle('Practice details'),
            TextField(
              controller: _court,
              decoration: const InputDecoration(labelText: 'Court practice'),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _office,
              decoration: const InputDecoration(labelText: 'Office address'),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _city,
              decoration: const InputDecoration(labelText: 'City'),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _bio,
              minLines: 3,
              maxLines: 6,
              decoration: const InputDecoration(
                labelText: 'Professional bio',
                alignLabelWithHint: true,
              ),
            ),
            const SizedBox(height: 14),
            FilledButton(
              onPressed: _filled ? _save : null,
              child: const Text('Save profile'),
            ),
          ],
        );
      },
    );
  }
}

class LawyerCaseDetailScreen extends StatefulWidget {
  const LawyerCaseDetailScreen({super.key, required this.caseId});

  final int caseId;

  @override
  State<LawyerCaseDetailScreen> createState() => _LawyerCaseDetailScreenState();
}

class _LawyerCaseDetailScreenState extends State<LawyerCaseDetailScreen> {
  late Future<Map<String, dynamic>> _future;
  late Future<List<Map<String, dynamic>>> _notesFuture;

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().lawyerCase(widget.caseId);
    _notesFuture = context.read<ApiService>().lawyerNotes(widget.caseId);
  }

  Future<void> _reloadNotes() async {
    setState(() {
      _notesFuture = context.read<ApiService>().lawyerNotes(widget.caseId);
    });
    await _notesFuture;
  }

  Future<void> _addNote() async {
    final controller = TextEditingController();
    final content = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add case note'),
        content: TextField(
          controller: controller,
          minLines: 3,
          maxLines: 8,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Note'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (content == null || content.isEmpty || !mounted) return;
    try {
      await context.read<ApiService>().addLawyerNote(widget.caseId, content);
      if (!mounted) return;
      await _reloadNotes();
      if (mounted) showInfoSnack(context, 'Note saved.');
    } on Exception catch (e) {
      if (mounted) showErrorSnack(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Case workspace')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _addNote,
        backgroundColor: AppColors.teal,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.note_add_outlined),
        label: const Text('Add note'),
      ),
      body: AsyncView<Map<String, dynamic>>(
        future: _future,
        onRetry: () => setState(() {
          _future = context.read<ApiService>().lawyerCase(widget.caseId);
        }),
        loadingText: 'Loading case…',
        builder: (context, data) {
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 90),
            children: [
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      firstNonEmpty([data['case_title'], 'Matter']),
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 8),
                    InfoRow(
                      'Client',
                      firstNonEmpty([data['client_name'], '—']),
                    ),
                    InfoRow(
                      'Client phone',
                      firstNonEmpty([data['client_phone'], '—']),
                    ),
                    InfoRow(
                      'Case number',
                      firstNonEmpty([data['case_number'], '—']),
                    ),
                    InfoRow('Court', firstNonEmpty([data['court_name'], '—'])),
                    InfoRow(
                      'Opposite party',
                      firstNonEmpty([data['opposite_party'], '—']),
                    ),
                    InfoRow('Status', firstNonEmpty([data['status'], '—'])),
                    InfoRow('CNR', firstNonEmpty([data['cnr_number'], '—'])),
                    InfoRow(
                      'Next hearing',
                      formatDate(data['external_next_hearing_date']),
                    ),
                  ],
                ),
              ),
              if (asString(data['case_description']).isNotEmpty) ...[
                const SizedBox(height: 14),
                const SectionTitle('Description'),
                AppCard(
                  child: Text(
                    cleanLegalText(data['case_description']),
                    style: const TextStyle(fontSize: 12.5, height: 1.5),
                  ),
                ),
              ],
              const SizedBox(height: 14),
              const SectionTitle('Confidential notes'),
              FutureBuilder<List<Map<String, dynamic>>>(
                future: _notesFuture,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const Padding(
                      padding: EdgeInsets.all(16),
                      child: Center(
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    );
                  }
                  final notes = snapshot.data ?? const [];
                  if (notes.isEmpty) {
                    return const AppCard(
                      child: Text(
                        'No notes yet.',
                        style: TextStyle(color: AppColors.muted),
                      ),
                    );
                  }
                  return Column(
                    children: [
                      for (final note in notes)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: AppCard(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  firstNonEmpty([note['title'], 'Note']),
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w600,
                                    fontSize: 12.5,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  asString(note['content']),
                                  style: const TextStyle(
                                    fontSize: 12.5,
                                    height: 1.45,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  formatDateTime(note['updated_at']),
                                  style: const TextStyle(
                                    fontSize: 10,
                                    color: AppColors.muted,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                    ],
                  );
                },
              ),
            ],
          );
        },
      ),
    );
  }
}
