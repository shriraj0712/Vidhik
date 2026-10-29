import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/format.dart';
import '../../models/legal.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';

class DocumentationScreen extends StatefulWidget {
  const DocumentationScreen({super.key});

  @override
  State<DocumentationScreen> createState() => _DocumentationScreenState();
}

class _DocumentationScreenState extends State<DocumentationScreen> {
  late Future<Map<String, dynamic>> _future;
  String? _category;
  String _search = '';

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<Map<String, dynamic>> _load() async {
    return context.read<ApiService>().documentationProcedures(
      category: _category,
      search: _search.isEmpty ? null : _search,
      limit: 100,
    );
  }

  void _reload() {
    setState(() {
      _future = _load();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Procedure checklists'),
        actions: [
          IconButton(onPressed: _reload, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
            child: TextField(
              onSubmitted: (value) {
                _search = value.trim();
                _reload();
              },
              decoration: InputDecoration(
                hintText: 'Search procedures, authorities or documents',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(
                  onPressed: _reload,
                  icon: const Icon(Icons.arrow_forward),
                ),
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
                final data = asMap(snapshot.data);
                final procedures = asMapList(data['procedures'])
                    .map(LegalProcedure.fromJson)
                    .toList();
                final categories = asMapList(data['categories'])
                    .map((e) => asString(e['category'] ?? e))
                    .where((e) => e.isNotEmpty)
                    .toList();
                return ListView(
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 28),
                  children: [
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        children: [
                          ChoiceChip(
                            label: const Text('All'),
                            selected: _category == null,
                            onSelected: (_) {
                              setState(() {
                                _category = null;
                              });
                              _reload();
                            },
                          ),
                          for (final category in categories)
                            Padding(
                              padding: const EdgeInsets.only(left: 7),
                              child: ChoiceChip(
                                label: Text(category),
                                selected: _category == category,
                                onSelected: (_) {
                                  setState(() {
                                    _category = category;
                                  });
                                  _reload();
                                },
                              ),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    SectionTitle(
                      '${asInt(data['total'], procedures.length)} procedures',
                      subtitle: 'Authoritative requirements with statutory references',
                    ),
                    if (procedures.isEmpty)
                      const AppCard(
                        child: Text(
                          'No procedures match this filter.',
                          style: TextStyle(color: AppColors.muted),
                        ),
                      )
                    else
                      for (final procedure in procedures)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 9),
                          child: AppCard(
                            onTap: () => Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) => ProcedureDetailScreen(
                                  procedureId: procedure.procedureId,
                                  title: procedure.procedureName,
                                ),
                              ),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  procedure.procedureName,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w600,
                                    fontSize: 13.5,
                                  ),
                                ),
                                const SizedBox(height: 3),
                                Text(
                                  procedure.description,
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    fontSize: 11.5,
                                    color: AppColors.muted,
                                    height: 1.4,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Wrap(
                                  spacing: 6,
                                  runSpacing: 5,
                                  children: [
                                    Tag(procedure.category),
                                    if (procedure.estimatedProcessingDays !=
                                        null)
                                      Tag(
                                        '~${procedure.estimatedProcessingDays} days',
                                        color: AppColors.accent,
                                      ),
                                    Tag(
                                      '${procedure.mandatoryDocumentsCount}/${procedure.totalDocumentsCount} docs',
                                      color: AppColors.info,
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
          ),
        ],
      ),
    );
  }
}

class ProcedureDetailScreen extends StatefulWidget {
  const ProcedureDetailScreen({
    super.key,
    required this.procedureId,
    required this.title,
  });

  final int procedureId;
  final String title;

  @override
  State<ProcedureDetailScreen> createState() => _ProcedureDetailScreenState();
}

class _ProcedureDetailScreenState extends State<ProcedureDetailScreen> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().documentationProcedure(
      widget.procedureId,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title, overflow: TextOverflow.ellipsis),
      ),
      body: AsyncView<Map<String, dynamic>>(
        future: _future,
        onRetry: () => setState(() {
          _future = context.read<ApiService>().documentationProcedure(
            widget.procedureId,
          );
        }),
        loadingText: 'Loading procedure…',
        builder: (context, data) {
          final mandatory = asMapList(data['mandatory_documents'])
              .map(DocumentRequirement.fromJson)
              .toList();
          final supporting = asMapList(data['supporting_documents'])
              .map(DocumentRequirement.fromJson)
              .toList();
          final portal = asString(data['official_portal_url']);
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
            children: [
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      firstNonEmpty([data['procedure_name'], widget.title]),
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      asString(data['description']),
                      style: const TextStyle(fontSize: 12.5, height: 1.5),
                    ),
                    const SizedBox(height: 10),
                    InfoRow('Category', firstNonEmpty([data['category'], '—'])),
                    InfoRow(
                      'Authority',
                      firstNonEmpty([data['authority_type'], '—']),
                    ),
                    InfoRow(
                      'Jurisdiction',
                      firstNonEmpty([data['jurisdiction'], '—']),
                    ),
                    InfoRow(
                      'Processing time',
                      data['estimated_processing_days'] == null
                          ? '—'
                          : '~${data['estimated_processing_days']} days',
                    ),
                    InfoRow(
                      'Governing law',
                      firstNonEmpty([data['governing_law_name'], '—']),
                    ),
                    InfoRow(
                      'Section',
                      firstNonEmpty([data['governing_section_number'], '—']),
                    ),
                  ],
                ),
              ),
              if (portal.isNotEmpty) ...[
                const SizedBox(height: 12),
                ExternalLinkButton(url: portal, label: 'Open official portal'),
              ],
              const SizedBox(height: 16),
              SectionTitle('Mandatory documents (${mandatory.length})'),
              if (mandatory.isEmpty)
                const AppCard(
                  child: Text(
                    'No mandatory documents recorded.',
                    style: TextStyle(color: AppColors.muted),
                  ),
                )
              else
                for (final doc in mandatory)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: _documentCard(doc, requiredDoc: true),
                  ),
              const SizedBox(height: 8),
              SectionTitle('Supporting documents (${supporting.length})'),
              if (supporting.isEmpty)
                const AppCard(
                  child: Text(
                    'No supporting documents recorded.',
                    style: TextStyle(color: AppColors.muted),
                  ),
                )
              else
                for (final doc in supporting)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: _documentCard(doc, requiredDoc: false),
                  ),
            ],
          );
        },
      ),
    );
  }

  Widget _documentCard(DocumentRequirement doc, {required bool requiredDoc}) {
    return AppCard(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            requiredDoc
                ? Icons.assignment_turned_in_outlined
                : Icons.attachment_outlined,
            size: 19,
            color: requiredDoc ? AppColors.teal : AppColors.muted,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  doc.documentName,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  doc.documentType,
                  style: const TextStyle(
                    fontSize: 10.5,
                    color: AppColors.muted,
                  ),
                ),
                if (doc.purpose.isNotEmpty) ...[
                  const SizedBox(height: 5),
                  Text(
                    doc.purpose,
                    style: const TextStyle(fontSize: 12, height: 1.4),
                  ),
                ],
                if (doc.preparationGuidance != null) ...[
                  const SizedBox(height: 5),
                  Text(
                    doc.preparationGuidance!,
                    style: const TextStyle(
                      fontSize: 11,
                      color: AppColors.muted,
                      height: 1.4,
                    ),
                  ),
                ],
                if (doc.sectionNumber != null) ...[
                  const SizedBox(height: 5),
                  Text(
                    '${doc.lawName ?? 'Act'} — Section ${doc.sectionNumber}',
                    style: const TextStyle(
                      fontSize: 10.5,
                      color: AppColors.teal,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
