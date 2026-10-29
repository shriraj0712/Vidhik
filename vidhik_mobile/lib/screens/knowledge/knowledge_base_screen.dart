import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/format.dart';
import '../../models/legal.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';

class KnowledgeBaseScreen extends StatefulWidget {
  const KnowledgeBaseScreen({super.key});

  @override
  State<KnowledgeBaseScreen> createState() => _KnowledgeBaseScreenState();
}

class _KnowledgeBaseScreenState extends State<KnowledgeBaseScreen> {
  late Future<_KnowledgeBundle> _future;
  String _filter = '';

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_KnowledgeBundle> _load() async {
    final api = context.read<ApiService>();
    final results = await Future.wait([api.knowledgeOverview(), api.acts()]);
    return _KnowledgeBundle(
      overview: results[0] as KnowledgeOverview,
      acts: results[1] as List<LawAct>,
    );
  }

  Future<void> _reload() async {
    setState(() {
      _future = _load();
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Legal knowledge base'),
        actions: [
          IconButton(onPressed: _reload, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: AsyncView<_KnowledgeBundle>(
        future: _future,
        onRetry: _reload,
        loadingText: 'Loading 24 central Acts…',
        builder: (context, bundle) {
          final filtered = _filter.isEmpty
              ? bundle.acts
              : bundle.acts
                    .where(
                      (a) => '${a.actName} ${a.shortName} ${a.category}'
                          .toLowerCase()
                          .contains(_filter),
                    )
                    .toList();
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [AppColors.navy, Color(0xFF145C66)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Bare Acts & statutory intelligence',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      bundle.overview.corpus,
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.75),
                        fontSize: 11.5,
                      ),
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        _heroStat(
                          '${bundle.overview.supportedStatutes.length}',
                          'Acts',
                        ),
                        _heroStat(
                          '${bundle.overview.totalOffences}',
                          'Offences',
                        ),
                        _heroStat(
                          '${bundle.overview.totalProcedures}',
                          'Procedures',
                        ),
                        _heroStat(
                          '${bundle.overview.totalVerifiedJudgments}',
                          'Judgments',
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              TextField(
                onChanged: (value) =>
                    setState(() => _filter = value.toLowerCase()),
                decoration: const InputDecoration(
                  hintText: 'Filter Acts by name or category',
                  prefixIcon: Icon(Icons.search),
                  isDense: true,
                ),
              ),
              const SizedBox(height: 16),
              SectionTitle(
                'Central Acts (${filtered.length})',
                subtitle:
                    'Tap an Act to review its offences and statutory metadata',
              ),
              for (final act in filtered)
                Padding(
                  padding: const EdgeInsets.only(bottom: 9),
                  child: AppCard(
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => ActDetailScreen(act: act),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 3,
                              ),
                              decoration: BoxDecoration(
                                color: AppColors.teal.withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                act.shortName,
                                style: const TextStyle(
                                  fontSize: 10.5,
                                  fontWeight: FontWeight.w700,
                                  color: AppColors.teal,
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                act.actName,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                  fontSize: 13.5,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 5),
                        Text(
                          [
                            '${act.year}',
                            act.category,
                            act.status,
                            '${act.totalSections} sections',
                          ].join(' · '),
                          style: const TextStyle(
                            fontSize: 11,
                            color: AppColors.muted,
                          ),
                        ),
                        if (act.offencesCount > 0 ||
                            act.proceduresCount > 0) ...[
                          const SizedBox(height: 7),
                          Wrap(
                            spacing: 6,
                            runSpacing: 5,
                            children: [
                              if (act.offencesCount > 0)
                                Tag(
                                  '${act.offencesCount} offences',
                                  color: AppColors.info,
                                ),
                              if (act.proceduresCount > 0)
                                Tag(
                                  '${act.proceduresCount} procedures',
                                  color: AppColors.success,
                                ),
                              if (act.evidenceCount > 0)
                                Tag(
                                  '${act.evidenceCount} evidence',
                                  color: AppColors.accent,
                                ),
                            ],
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              if (bundle.overview.supportedStatutes.isNotEmpty) ...[
                const SizedBox(height: 16),
                const SectionTitle('Corpus coverage'),
                AppCard(
                  child: Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      for (final statute in bundle.overview.supportedStatutes)
                        Tag(statute, color: AppColors.navy),
                    ],
                  ),
                ),
              ],
            ],
          );
        },
      ),
    );
  }

  Widget _heroStat(String value, String label) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.w700,
            ),
          ),
          Text(
            label,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.65),
              fontSize: 10,
            ),
          ),
        ],
      ),
    );
  }
}

class _KnowledgeBundle {
  const _KnowledgeBundle({required this.overview, required this.acts});

  final KnowledgeOverview overview;
  final List<LawAct> acts;
}

class ActDetailScreen extends StatefulWidget {
  const ActDetailScreen({super.key, required this.act});

  final LawAct act;

  @override
  State<ActDetailScreen> createState() => _ActDetailScreenState();
}

class _ActDetailScreenState extends State<ActDetailScreen> {
  late Future<List<Map<String, dynamic>>> _offencesFuture;

  @override
  void initState() {
    super.initState();
    _offencesFuture = context.read<ApiService>().offences(
      lawId: widget.act.actId,
    );
  }

  @override
  Widget build(BuildContext context) {
    final act = widget.act;
    return Scaffold(
      appBar: AppBar(title: Text(act.shortName)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
        children: [
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  act.actName,
                  style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                InfoRow('Act number', act.actNumber ?? '—'),
                InfoRow('Year', '${act.year}'),
                InfoRow('Category', act.category),
                InfoRow('Jurisdiction', act.jurisdiction),
                InfoRow('Status', act.status),
                InfoRow('Sections', '${act.totalSections}'),
                if (act.amendmentDetails != null)
                  InfoRow('Amendments', act.amendmentDetails!),
                InfoRow('Judgments', act.judgmentsStatus),
                if (act.authorities.isNotEmpty)
                  InfoRow('Authorities', act.authorities.join(', ')),
              ],
            ),
          ),
          const SizedBox(height: 16),
          SectionTitle('Offences (${act.offencesCount})'),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _offencesFuture,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Padding(
                  padding: EdgeInsets.all(20),
                  child: Center(
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                );
              }
              if (snapshot.hasError) {
                return AppCard(
                  child: Text(
                    '${snapshot.error}'.replaceFirst('ApiException: ', ''),
                    style: const TextStyle(fontSize: 12),
                  ),
                );
              }
              final offences = snapshot.data ?? const [];
              if (offences.isEmpty) {
                return const AppCard(
                  child: Text(
                    'No offence records are linked to this Act in the knowledge base.',
                    style: TextStyle(color: AppColors.muted),
                  ),
                );
              }
              return Column(
                children: [
                  for (final offence in offences)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 9),
                      child: AppCard(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    firstNonEmpty([
                                      offence['offence_name'],
                                      'Offence',
                                    ]),
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w600,
                                      fontSize: 13.5,
                                    ),
                                  ),
                                ),
                                Tag(
                                  'S. ${firstNonEmpty([offence['section_number'], '—'])}',
                                ),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Text(
                              firstNonEmpty([offence['section_title'], '']),
                              style: const TextStyle(
                                fontSize: 11.5,
                                color: AppColors.muted,
                              ),
                            ),
                            if (asString(offence['description'])
                                .isNotEmpty) ...[
                              const SizedBox(height: 6),
                              Text(
                                asString(offence['description']),
                                maxLines: 3,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontSize: 12,
                                  height: 1.4,
                                ),
                              ),
                            ],
                            const SizedBox(height: 8),
                            Wrap(
                              spacing: 6,
                              runSpacing: 5,
                              children: [
                                if (asString(offence['cognizable_status'])
                                    .isNotEmpty)
                                  Tag(
                                    firstNonEmpty([
                                      offence['cognizable_status'],
                                      '',
                                    ]),
                                    color: AppColors.info,
                                  ),
                                if (asString(offence['bailable_status'])
                                    .isNotEmpty)
                                  Tag(
                                    firstNonEmpty([
                                      offence['bailable_status'],
                                      '',
                                    ]),
                                    color: AppColors.warning,
                                  ),
                                if (asString(offence['triable_by']).isNotEmpty)
                                  Tag(
                                    firstNonEmpty([offence['triable_by'], '']),
                                    color: AppColors.navy,
                                  ),
                              ],
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
      ),
    );
  }
}
