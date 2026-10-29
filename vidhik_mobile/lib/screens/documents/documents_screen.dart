import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/format.dart';
import '../../models/citizen.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';

class DocumentsScreen extends StatefulWidget {
  const DocumentsScreen({super.key});

  @override
  State<DocumentsScreen> createState() => _DocumentsScreenState();
}

class _DocumentsScreenState extends State<DocumentsScreen> {
  late Future<List<CitizenDocument>> _future;
  String _filter = '';

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().citizenDocuments();
  }

  Future<void> _reload() async {
    setState(() {
      _future = context.read<ApiService>().citizenDocuments();
    });
    await _future;
  }

  Future<void> _openUpload() async {
    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const _CatalogDocumentSheet(),
    );
    if (saved == true) _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My documents'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _reload,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openUpload,
        backgroundColor: AppColors.teal,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.upload_file),
        label: const Text('Add document'),
      ),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 6),
              child: Column(
                children: [
                  TextField(
                    onChanged: (value) =>
                        setState(() => _filter = value.toLowerCase()),
                    decoration: const InputDecoration(
                      hintText: 'Filter by document name or type',
                      prefixIcon: Icon(Icons.search),
                      isDense: true,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppColors.info.withValues(alpha: 0.06),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(
                          Icons.info_outline,
                          size: 15,
                          color: AppColors.info,
                        ),
                        SizedBox(width: 7),
                        Expanded(
                          child: Text(
                            'The VIDHIK backend catalogues case documents and links them to your matters. '
                            'To extract clauses and risks from the actual file, use Document Analysis.',
                            style: TextStyle(
                              fontSize: 11,
                              color: AppColors.muted,
                              height: 1.4,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: AsyncView<List<CitizenDocument>>(
                future: _future,
                onRetry: _reload,
                loadingText: 'Loading your documents…',
                builder: (context, documents) {
                  final filtered = _filter.isEmpty
                      ? documents
                      : documents
                            .where(
                              (d) =>
                                  '${d.documentName} ${d.documentType} ${d.caseTitle ?? ''}'
                                      .toLowerCase()
                                      .contains(_filter),
                            )
                            .toList();
                  if (filtered.isEmpty) {
                    return EmptyState(
                      title: 'No documents catalogued',
                      message: 'Attach legal filings, notices, affidavits and evidence records to a matter.',
                      icon: Icons.folder_copy_outlined,
                      action: FilledButton.icon(
                        onPressed: _openUpload,
                        icon: const Icon(Icons.add),
                        label: const Text('Add a document'),
                      ),
                    );
                  }
                  return ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 90),
                    itemCount: filtered.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 9),
                    itemBuilder: (context, index) =>
                        _documentCard(filtered[index]),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _documentCard(CitizenDocument document) {
    return AppCard(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: AppColors.teal.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(
              Icons.description_outlined,
              color: AppColors.teal,
              size: 20,
            ),
          ),
          const SizedBox(width: 11),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  document.documentName,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  [
                    document.documentType,
                    document.readableSize,
                    document.uploadStatus,
                  ].join(' · '),
                  style: const TextStyle(
                    fontSize: 11.5,
                    color: AppColors.muted,
                  ),
                ),
                if (document.caseTitle != null) ...[
                  const SizedBox(height: 5),
                  Text(
                    'Matter: ${document.caseTitle}',
                    style: const TextStyle(
                      fontSize: 11.5,
                      color: AppColors.teal,
                    ),
                  ),
                ],
                if (document.description != null) ...[
                  const SizedBox(height: 5),
                  Text(
                    document.description!,
                    style: const TextStyle(fontSize: 12, height: 1.4),
                  ),
                ],
                const SizedBox(height: 6),
                Text(
                  'Added ${formatDate(document.createdAt)}',
                  style: const TextStyle(
                    fontSize: 10.5,
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
}

class _CatalogDocumentSheet extends StatefulWidget {
  const _CatalogDocumentSheet();

  @override
  State<_CatalogDocumentSheet> createState() => _CatalogDocumentSheetState();
}

class _CatalogDocumentSheetState extends State<_CatalogDocumentSheet> {
  final _name = TextEditingController();
  final _description = TextEditingController();
  String _type = 'General';
  int? _caseId;
  List<CitizenCase> _cases = [];
  bool _loadingCases = true;
  bool _busy = false;
  String? _error;

  static const _types = [
    'General',
    'Affidavit',
    'Petition',
    'Notice',
    'Agreement',
    'Evidence',
    'Court Order',
    'Identity Proof',
    'Financial Record',
  ];

  @override
  void initState() {
    super.initState();
    _loadCases();
  }

  Future<void> _loadCases() async {
    try {
      final cases = await context.read<ApiService>().citizenCases();
      if (!mounted) return;
      setState(() {
        _cases = cases;
        _loadingCases = false;
        _caseId = cases.isNotEmpty ? cases.first.caseId : null;
      });
    } catch (_) {
      if (mounted) {
        setState(() {
          _loadingCases = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _name.dispose();
    _description.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_caseId == null) {
      setState(() {
        _error = 'Register a case before attaching documents.';
      });
      return;
    }
    if (_name.text.trim().length < 2) {
      setState(() {
        _error = 'Enter a document name.';
      });
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await context.read<ApiService>().uploadCitizenDocument({
        'case_id': _caseId,
        'document_name': _name.text.trim(),
        'document_type': _type,
        'description': _description.text.trim().isEmpty
            ? null
            : _description.text.trim(),
      });
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } on Exception catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e'.replaceFirst('ApiException: ', '');
      });
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(22)),
      ),
      child: SafeArea(
        top: false,
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Add a case document',
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 4),
              const Text(
                'Catalogues the document and links it to a matter. The backend records metadata; '
                'it does not store the file binary on this endpoint.',
                style: TextStyle(
                  fontSize: 11.5,
                  color: AppColors.muted,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 14),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    _error!,
                    style: const TextStyle(
                      color: AppColors.danger,
                      fontSize: 12,
                    ),
                  ),
                ),
              if (_loadingCases)
                const Center(
                  child: Padding(
                    padding: EdgeInsets.all(8),
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                )
              else if (_cases.isEmpty)
                const AppCard(
                  child: Text(
                    'No cases registered. Create a case first, then attach documents.',
                    style: TextStyle(fontSize: 12.5, color: AppColors.muted),
                  ),
                )
              else
                DropdownButtonFormField<int>(
                  initialValue: _caseId,
                  isExpanded: true,
                  decoration: const InputDecoration(labelText: 'Linked case'),
                  items: [
                    for (final item in _cases)
                      DropdownMenuItem(
                        value: item.caseId,
                        child: Text(
                          item.title,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                  ],
                  onChanged: (value) => setState(() => _caseId = value),
                ),
              const SizedBox(height: 10),
              TextField(
                controller: _name,
                decoration: const InputDecoration(labelText: 'Document name'),
              ),
              const SizedBox(height: 10),
              DropdownButtonFormField<String>(
                initialValue: _type,
                decoration: const InputDecoration(labelText: 'Document type'),
                items: [
                  for (final type in _types)
                    DropdownMenuItem(value: type, child: Text(type)),
                ],
                onChanged: (value) =>
                    setState(() => _type = value ?? 'General'),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _description,
                minLines: 2,
                maxLines: 4,
                decoration: const InputDecoration(
                  labelText: 'Description (optional)',
                ),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: _busy || _cases.isEmpty ? null : _save,
                child: _busy
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2.2,
                          color: Colors.white,
                        ),
                      )
                    : const Text('Save document'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
