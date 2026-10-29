import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/format.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';

class DocumentAnalysisScreen extends StatefulWidget {
  const DocumentAnalysisScreen({super.key});

  @override
  State<DocumentAnalysisScreen> createState() => _DocumentAnalysisScreenState();
}

class _DocumentAnalysisScreenState extends State<DocumentAnalysisScreen> {
  late Future<Map<String, dynamic>> _historyFuture;

  final _text = TextEditingController();
  final _title = TextEditingController();
  String? _filePath;
  String? _fileName;
  bool _pasteMode = false;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _historyFuture = context.read<ApiService>().analysisHistory();
  }

  @override
  void dispose() {
    _text.dispose();
    _title.dispose();
    super.dispose();
  }

  Future<void> _pickFile() async {
    try {
      final file = await FilePicker.pickFile(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'docx', 'txt'],
      );
      if (file == null) return;
      if (file.path == null) {
        setState(() {
          _error = 'The selected file could not be read on this device.';
        });
        return;
      }
      setState(() {
        _filePath = file.path;
        _fileName = file.name;
        if (_title.text.trim().isEmpty) _title.text = file.name;
        _error = null;
      });
    } catch (e) {
      setState(() {
        _error = 'Could not open the file picker: $e';
      });
    }
  }

  Future<void> _analyse() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final api = context.read<ApiService>();
      Map<String, dynamic> result;
      if (_pasteMode) {
        if (_text.text.trim().length < 10) {
          throw Exception('Paste at least 10 characters of legal text.');
        }
        result = await api.analyzeDocumentText(
          text: _text.text.trim(),
          documentTitle: _title.text.trim().isEmpty
              ? 'Pasted legal text'
              : _title.text.trim(),
        );
      } else {
        if (_filePath == null) {
          throw Exception('Choose a PDF, DOCX or TXT file first.');
        }
        result = await api.analyzeDocumentFile(
          _filePath!,
          documentTitle: _title.text.trim().isEmpty ? null : _title.text.trim(),
        );
      }
      if (!mounted) return;
      setState(() {
        _historyFuture = api.analysisHistory();
      });
      Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => AnalysisResultScreen(result: result)),
      );
    } on Exception catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e'
            .replaceFirst('Exception: ', '')
            .replaceFirst('ApiException: ', '');
      });
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  Future<void> _openHistoryItem(int analysisId) async {
    try {
      final result = await context.read<ApiService>().analysisDetail(
        analysisId,
      );
      if (!mounted) return;
      Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => AnalysisResultScreen(result: result)),
      );
    } on Exception catch (e) {
      if (mounted) showErrorSnack(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Document analysis')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
        children: [
          const AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.find_in_page_outlined, color: AppColors.teal),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Review contracts, notices and filings',
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 14,
                        ),
                      ),
                    ),
                  ],
                ),
                SizedBox(height: 8),
                Text(
                  'VIDHIK extracts parties, dates, clauses, obligations and potential risks, then cross-references '
                  'verified statutory provisions from its database. This is research support, not legal advice.',
                  style: TextStyle(
                    fontSize: 12,
                    color: AppColors.muted,
                    height: 1.45,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          SegmentedButton<bool>(
            segments: const [
              ButtonSegment(
                value: false,
                label: Text('Upload file'),
                icon: Icon(Icons.upload_file),
              ),
              ButtonSegment(
                value: true,
                label: Text('Paste text'),
                icon: Icon(Icons.text_snippet_outlined),
              ),
            ],
            selected: {_pasteMode},
            onSelectionChanged: (values) =>
                setState(() => _pasteMode = values.first),
          ),
          const SizedBox(height: 14),
          if (_error != null)
            Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppColors.danger.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(9),
              ),
              child: Text(
                _error!,
                style: const TextStyle(
                  color: AppColors.danger,
                  fontSize: 12,
                  height: 1.4,
                ),
              ),
            ),
          if (!_pasteMode)
            AppCard(
              onTap: _busy ? null : _pickFile,
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppColors.teal.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.attach_file, color: AppColors.teal),
                  ),
                  const SizedBox(width: 11),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _fileName ?? 'Choose a legal document',
                          style: const TextStyle(
                            fontWeight: FontWeight.w600,
                            fontSize: 13.5,
                          ),
                        ),
                        const SizedBox(height: 2),
                        const Text(
                          'PDF, DOCX or TXT',
                          style: TextStyle(
                            fontSize: 11,
                            color: AppColors.muted,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Icon(Icons.chevron_right, color: AppColors.muted),
                ],
              ),
            )
          else
            TextField(
              controller: _text,
              minLines: 6,
              maxLines: 12,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(
                labelText: 'Paste contract, notice or legal text',
                alignLabelWithHint: true,
              ),
            ),
          const SizedBox(height: 10),
          TextField(
            controller: _title,
            decoration: const InputDecoration(
              labelText: 'Document title (optional)',
            ),
          ),
          const SizedBox(height: 14),
          FilledButton.icon(
            onPressed: _busy ? null : _analyse,
            icon: _busy
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.search),
            label: Text(_busy ? 'Analysing document…' : 'Analyse document'),
          ),
          if (_busy) ...[
            const SizedBox(height: 10),
            const Text(
              'Extraction and statutory cross-referencing can take a little longer for large documents.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 11, color: AppColors.muted),
            ),
          ],
          const SizedBox(height: 22),
          const SectionTitle(
            'Past analyses',
            subtitle: 'Only analyses linked to your account',
          ),
          FutureBuilder<Map<String, dynamic>>(
            future: _historyFuture,
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
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${snapshot.error}'.replaceFirst('ApiException: ', ''),
                        style: const TextStyle(fontSize: 12),
                      ),
                      const SizedBox(height: 8),
                      TextButton(
                        onPressed: () => setState(() {
                          _historyFuture = context
                              .read<ApiService>()
                              .analysisHistory();
                        }),
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                );
              }
              final analyses = asMapList(asMap(snapshot.data)['analyses']);
              if (analyses.isEmpty) {
                return const AppCard(
                  child: Text(
                    'No document analyses yet.',
                    style: TextStyle(color: AppColors.muted),
                  ),
                );
              }
              return Column(
                children: [
                  for (final item in analyses)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: AppCard(
                        onTap: () =>
                            _openHistoryItem(asInt(item['analysis_id'])),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    firstNonEmpty([
                                      item['document_name'],
                                      'Document',
                                    ]),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w600,
                                      fontSize: 13.5,
                                    ),
                                  ),
                                ),
                                Tag(
                                  firstNonEmpty([
                                    item['document_type'],
                                    'Unclassified',
                                  ]),
                                ),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Text(
                              firstNonEmpty([item['summary_preview'], '']),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontSize: 12,
                                color: AppColors.muted,
                                height: 1.4,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              '${asInt(item['risks_count'])} risks · '
                              '${asInt(item['verified_references_count'])} verified references · '
                              '${formatDate(item['created_at'])}',
                              style: const TextStyle(
                                fontSize: 10.5,
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
      ),
    );
  }
}

class AnalysisResultScreen extends StatelessWidget {
  const AnalysisResultScreen({super.key, required this.result});

  final Map<String, dynamic> result;

  Future<void> _saveToCase(BuildContext context) async {
    final controller = TextEditingController();
    final caseId = await showDialog<int>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Save to case'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Lawyer case ID'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              final id = int.tryParse(controller.text.trim());
              Navigator.pop(context, id);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (caseId == null || !context.mounted) return;
    try {
      final response = await context.read<ApiService>().saveAnalysisToCase(
        asInt(result['analysis_id']),
        {
          'case_id': caseId,
          'save_as_document': true,
          'save_summary_note': true,
          'link_verified_sections': true,
        },
      );
      if (context.mounted) {
        showInfoSnack(
          context,
          '${response['message'] ?? 'Analysis saved to case.'}',
        );
      }
    } on Exception catch (e) {
      if (context.mounted) showErrorSnack(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final risks = asMapList(result['identified_risks']);
    final clauses = asMapList(result['clauses']);
    final parties = asMapList(result['parties']);
    final dates = asMapList(result['dates']);
    final amounts = asMapList(result['monetary_values']);
    final references = asMapList(result['legal_references']);
    final actions = asMapList(result['action_items']);
    final missing = asMapList(result['missing_information']);
    final responsibilities = asMapList(result['obligations_and_rights']);

    return Scaffold(
      appBar: AppBar(title: const Text('Analysis report')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
        children: [
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  firstNonEmpty([result['document_name'], 'Document']),
                  style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 4),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    Tag(
                      firstNonEmpty([result['document_type'], 'Unclassified']),
                    ),
                    Tag(
                      firstNonEmpty([result['file_type'], 'file']),
                      color: AppColors.info,
                    ),
                    if (asInt(result['analysis_id']) > 0)
                      Tag('#${result['analysis_id']}', color: AppColors.muted),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  asString(result['summary']),
                  style: const TextStyle(fontSize: 13, height: 1.55),
                ),
                if (asMapList(result['executive_takeaways']).isNotEmpty) ...[
                  const SizedBox(height: 10),
                  BulletList(
                    asMapList(result['executive_takeaways'])
                        .map((e) => asString(e))
                        .where((e) => e.isNotEmpty)
                        .toList(),
                  ),
                ],
                if (asString(result['warning_message']).isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(
                    asString(result['warning_message']),
                    style: const TextStyle(
                      fontSize: 12,
                      color: AppColors.warning,
                    ),
                  ),
                ],
              ],
            ),
          ),
          if (parties.isNotEmpty) ...[
            const SizedBox(height: 14),
            const SectionTitle('Parties'),
            AppCard(
              child: Column(
                children: [
                  for (final party in parties)
                    InfoRow(
                      firstNonEmpty([party['role'], 'Party']),
                      firstNonEmpty([party['name'], '—']),
                    ),
                ],
              ),
            ),
          ],
          if (dates.isNotEmpty) ...[
            const SizedBox(height: 14),
            const SectionTitle('Dates'),
            AppCard(
              child: Column(
                children: [
                  for (final date in dates)
                    InfoRow(
                      firstNonEmpty([date['label'], 'Date']),
                      firstNonEmpty([date['date_str'], '—']),
                    ),
                ],
              ),
            ),
          ],
          if (amounts.isNotEmpty) ...[
            const SizedBox(height: 14),
            const SectionTitle('Monetary values'),
            AppCard(
              child: Column(
                children: [
                  for (final amount in amounts)
                    InfoRow(
                      firstNonEmpty([amount['label'], 'Amount']),
                      firstNonEmpty([amount['amount_text'], '—']),
                    ),
                ],
              ),
            ),
          ],
          if (risks.isNotEmpty) ...[
            const SizedBox(height: 14),
            SectionTitle('Potential risks (${risks.length})'),
            for (final risk in risks)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              firstNonEmpty([risk['title'], 'Risk']),
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                                fontSize: 13,
                              ),
                            ),
                          ),
                          Tag(
                            firstNonEmpty([risk['severity'], 'Medium']),
                            color: AppColors.riskColor(
                              firstNonEmpty([risk['severity'], '']),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 5),
                      Text(
                        asString(risk['description']),
                        style: const TextStyle(fontSize: 12.5, height: 1.45),
                      ),
                      if (asString(risk['recommendation']).isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Text(
                          'Recommended: ${risk['recommendation']}',
                          style: const TextStyle(
                            fontSize: 11.5,
                            color: AppColors.teal,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
          ],
          if (clauses.isNotEmpty) ...[
            const SizedBox(height: 10),
            SectionTitle('Key clauses (${clauses.length})'),
            for (final clause in clauses)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        firstNonEmpty([clause['title'], 'Clause']),
                        style: const TextStyle(
                          fontWeight: FontWeight.w600,
                          fontSize: 13,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        firstNonEmpty([clause['category'], '']),
                        style: const TextStyle(
                          fontSize: 11,
                          color: AppColors.teal,
                        ),
                      ),
                      if (asString(clause['text_excerpt']).isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Text(
                          asString(clause['text_excerpt']),
                          maxLines: 5,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontSize: 12,
                            height: 1.45,
                            color: AppColors.muted,
                          ),
                        ),
                      ],
                      if (asString(clause['explanation']).isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Text(
                          asString(clause['explanation']),
                          style: const TextStyle(fontSize: 12.5, height: 1.45),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
          ],
          if (responsibilities.isNotEmpty) ...[
            const SizedBox(height: 10),
            const SectionTitle('Obligations & rights'),
            for (final item in responsibilities)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${firstNonEmpty([item['party'], 'Party'])} · ${firstNonEmpty([item['type'], ''])}',
                        style: const TextStyle(
                          fontWeight: FontWeight.w600,
                          fontSize: 12.5,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        asString(item['description']),
                        style: const TextStyle(fontSize: 12.5, height: 1.4),
                      ),
                    ],
                  ),
                ),
              ),
          ],
          if (references.isNotEmpty) ...[
            const SizedBox(height: 10),
            SectionTitle('Statutory references (${references.length})'),
            for (final reference in references)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              firstNonEmpty([
                                reference['section_title'],
                                reference['citation_text'],
                                'Reference',
                              ]),
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                                fontSize: 12.5,
                              ),
                            ),
                          ),
                          Tag(
                            asBool(reference['is_verified_in_db'])
                                ? 'Verified'
                                : 'Unverified',
                            color: asBool(reference['is_verified_in_db'])
                                ? AppColors.success
                                : AppColors.warning,
                          ),
                        ],
                      ),
                      const SizedBox(height: 3),
                      Text(
                        [
                          firstNonEmpty([reference['law_name'], '']),
                          if (asString(reference['section_number']).isNotEmpty)
                            'Section ${reference['section_number']}',
                          firstNonEmpty([reference['citation_text'], '']),
                        ].where((e) => e.isNotEmpty).join(' · '),
                        style: const TextStyle(
                          fontSize: 11,
                          color: AppColors.muted,
                        ),
                      ),
                      if (asString(reference['relevance_explanation'])
                          .isNotEmpty) ...[
                        const SizedBox(height: 5),
                        Text(
                          asString(reference['relevance_explanation']),
                          style: const TextStyle(fontSize: 12, height: 1.4),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
          ],
          if (missing.isNotEmpty) ...[
            const SizedBox(height: 10),
            const SectionTitle('Missing information'),
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (final item in missing)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Text(
                        '• ${firstNonEmpty([item['item'], 'Item'])}: ${firstNonEmpty([item['description'], ''])}',
                        style: const TextStyle(fontSize: 12.5, height: 1.45),
                      ),
                    ),
                ],
              ),
            ),
          ],
          if (actions.isNotEmpty) ...[
            const SizedBox(height: 10),
            const SectionTitle('Action items'),
            for (final action in actions)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: AppCard(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(
                        Icons.check_circle_outline,
                        size: 16,
                        color: AppColors.teal,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              firstNonEmpty([action['task'], 'Action']),
                              style: const TextStyle(fontSize: 12.5),
                            ),
                            if (asString(action['deadline_or_trigger'])
                                .isNotEmpty)
                              Text(
                                'Trigger: ${action['deadline_or_trigger']}',
                                style: const TextStyle(
                                  fontSize: 11,
                                  color: AppColors.muted,
                                ),
                              ),
                          ],
                        ),
                      ),
                      Tag(firstNonEmpty([action['priority'], 'Medium'])),
                    ],
                  ),
                ),
              ),
          ],
          const SizedBox(height: 18),
          if (auth.isLawyer && asInt(result['analysis_id']) > 0)
            OutlinedButton.icon(
              onPressed: () => _saveToCase(context),
              icon: const Icon(Icons.folder_special_outlined),
              label: const Text('Save analysis to a case'),
            ),
          const SizedBox(height: 10),
          Text(
            asString(
              result['disclaimer'],
              'Analysis is research support and does not constitute formal legal advice.',
            ),
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 10.5,
              color: AppColors.muted,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }
}
