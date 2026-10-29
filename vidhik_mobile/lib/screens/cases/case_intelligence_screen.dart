import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/format.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';

class CaseIntelligenceScreen extends StatefulWidget {
  const CaseIntelligenceScreen({super.key, this.caseId});

  final int? caseId;

  @override
  State<CaseIntelligenceScreen> createState() => _CaseIntelligenceScreenState();
}

class _CaseIntelligenceScreenState extends State<CaseIntelligenceScreen> {
  late Future<Map<String, dynamic>?> _future;
  int? _resolvedCaseId;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<Map<String, dynamic>?> _load() async {
    final api = context.read<ApiService>();
    if (widget.caseId != null) {
      _resolvedCaseId = widget.caseId;
      return api.caseContext(widget.caseId!);
    }
    final active = await api.activeCase();
    final id = active['active_case_id'];
    if (id == null) return null;
    _resolvedCaseId = asInt(id);
    final contextMap = asMap(active['context']);
    if (contextMap.isNotEmpty) return contextMap;
    return api.caseContext(_resolvedCaseId!);
  }

  Future<void> _reload() async {
    setState(() {
      _future = _load();
    });
    await _future;
  }

  void _showAnalysis(Map<String, dynamic> context) {
    setState(() {
      _future = Future.value(context);
    });
    final id = asInt(context['case_id']);
    if (id > 0) _resolvedCaseId = id;
  }

  Future<void> _addInformation(Map<String, dynamic> data) async {
    final id = asInt(data['case_id']);
    if (id <= 0) return;
    final updated = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _AdditionalFactsSheet(caseId: id),
    );
    if (updated != null && mounted) _showAnalysis(updated);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Case intelligence'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _reload,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: AsyncView<Map<String, dynamic>?>(
        future: _future,
        onRetry: _reload,
        loadingText: 'Analysing your situation against the statutory corpus…',
        builder: (context, data) {
          if (data == null || data.isEmpty) {
            return _CaseIntakeForm(onAnalysed: _showAnalysis);
          }
          return _buildContext(context, data);
        },
      ),
    );
  }

  Widget _buildContext(BuildContext context, Map<String, dynamic> data) {
    final title = firstNonEmpty([
      data['title'],
      data['case_title'],
      'Case analysis',
    ]);
    final urgency = firstNonEmpty([data['urgency'], 'Medium']);
    final provisions = asMapList(data['ranked_provisions']);
    final authorities = asMapList(data['recommended_authorities']);
    final lawyers = asMapList(data['recommended_lawyers']);
    final actions = asMap(data['recommended_actions']);
    final documents = asMap(data['required_documents']);
    final procedure = asMap(data['further_procedure']);
    final emotional = asMap(data['emotional_indicators']);

    return RefreshIndicator(
      onRefresh: _reload,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
        children: [
          Container(
            padding: const EdgeInsets.all(17),
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
                Text(
                  title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 7,
                  runSpacing: 6,
                  children: [
                    _heroTag(firstNonEmpty([data['case_category'], 'General'])),
                    _heroTag(
                      firstNonEmpty([data['legal_domain'], 'Indian law']),
                    ),
                    _heroTag('Urgency: $urgency'),
                    _heroTag('v${asInt(data['analysis_version'], 1)}'),
                  ],
                ),
                if (asString(data['situation_summary']).isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Text(
                    asString(data['situation_summary']),
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.85),
                      fontSize: 12.5,
                      height: 1.5,
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),
          _bulletSection(
            'Facts explicitly stated',
            asMapList(data['explicit_facts'])
                .map((e) => asString(e))
                .where((e) => e.isNotEmpty)
                .toList(),
          ),
          _bulletSection(
            'Identified legal issues',
            asMapList(data['identified_issues'])
                .map((e) => asString(e))
                .where((e) => e.isNotEmpty)
                .toList(),
          ),
          _bulletSection(
            'Uncertain or unconfirmed facts',
            asMapList(data['uncertain_facts'])
                .map((e) => asString(e))
                .where((e) => e.isNotEmpty)
                .toList(),
          ),
          _bulletSection(
            'Missing information',
            asMapList(data['missing_information'])
                .map((e) => asString(e))
                .where((e) => e.isNotEmpty)
                .toList(),
          ),
          const SizedBox(height: 6),
          SectionTitle(
            'Ranked statutory provisions',
            subtitle:
                '${provisions.length} provision(s) retrieved from the Vidhik database',
          ),
          if (provisions.isEmpty)
            const AppCard(
              child: Text(
                'No directly matching provision was retrieved. Add more facts or use legal research.',
                style: TextStyle(color: AppColors.muted),
              ),
            )
          else
            for (final provision in provisions)
              Padding(
                padding: const EdgeInsets.only(bottom: 9),
                child: _provisionCard(provision),
              ),
          const SizedBox(height: 8),
          _actionPlan(actions),
          _documentChecklist(documents),
          _procedure(procedure),
          if (authorities.isNotEmpty) ...[
            const SizedBox(height: 8),
            const SectionTitle('Recommended authorities'),
            for (final authority in authorities)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        firstNonEmpty([
                          authority['authority_name'],
                          'Authority',
                        ]),
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        [
                          firstNonEmpty([authority['authority_type'], '']),
                          firstNonEmpty([authority['jurisdiction_level'], '']),
                        ].where((e) => e.isNotEmpty).join(' · '),
                        style: const TextStyle(
                          fontSize: 11.5,
                          color: AppColors.muted,
                        ),
                      ),
                      if (asString(authority['role_in_case']).isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Text(
                          asString(authority['role_in_case']),
                          style: const TextStyle(fontSize: 12.5, height: 1.4),
                        ),
                      ],
                      if (asString(authority['filing_channel']).isNotEmpty) ...[
                        const SizedBox(height: 5),
                        Text(
                          'Channel: ${authority['filing_channel']}',
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
          if (lawyers.isNotEmpty) ...[
            const SizedBox(height: 8),
            const SectionTitle('Matched advocates'),
            for (final lawyer in lawyers)
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
                              firstNonEmpty([lawyer['full_name'], 'Advocate']),
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                          Tag(
                            '${asDouble(lawyer['match_score']).toStringAsFixed(0)}% match',
                          ),
                        ],
                      ),
                      const SizedBox(height: 3),
                      Text(
                        '${firstNonEmpty([lawyer['specialization'], 'General practice'])}'
                        '${lawyer['experience_years'] != null ? ' · ${lawyer['experience_years']} yrs' : ''}',
                        style: const TextStyle(
                          fontSize: 11.5,
                          color: AppColors.muted,
                        ),
                      ),
                      if (asString(lawyer['match_reason']).isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Text(
                          asString(lawyer['match_reason']),
                          style: const TextStyle(fontSize: 12, height: 1.4),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
          ],
          if (emotional.isNotEmpty) ...[
            const SizedBox(height: 8),
            const SectionTitle('Communication adaptation'),
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  BulletList(
                    asMapList(emotional['detected_indicators'])
                        .map((e) => asString(e))
                        .where((e) => e.isNotEmpty)
                        .toList(),
                    emptyText: 'No strong emotional indicators detected.',
                  ),
                  if (asString(emotional['communication_adaptation'])
                      .isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Text(
                      asString(emotional['communication_adaptation']),
                      style: const TextStyle(fontSize: 12.5, height: 1.45),
                    ),
                  ],
                  if (emotional['safety_indicators_present'] == true &&
                      asString(emotional['immediate_safety_notice'])
                          .isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Text(
                      asString(emotional['immediate_safety_notice']),
                      style: const TextStyle(
                        fontSize: 12.5,
                        color: AppColors.danger,
                        height: 1.4,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
          const SizedBox(height: 18),
          OutlinedButton.icon(
            onPressed: () => _addInformation(data),
            icon: const Icon(Icons.add_circle_outline),
            label: const Text('Add new facts and re-analyse'),
          ),
          const SizedBox(height: 8),
          Text(
            'Case analysis is decision support grounded in statutory text. It does not establish liability or replace an advocate.',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 10.5,
              color: AppColors.muted,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }

  Widget _heroTag(String text) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
    decoration: BoxDecoration(
      color: Colors.white.withValues(alpha: 0.12),
      borderRadius: BorderRadius.circular(999),
    ),
    child: Text(
      text,
      style: const TextStyle(
        color: Colors.white,
        fontSize: 10,
        fontWeight: FontWeight.w500,
      ),
    ),
  );

  Widget _bulletSection(String title, List<String> items) {
    if (items.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 13.5,
              ),
            ),
            const SizedBox(height: 8),
            BulletList(items),
          ],
        ),
      ),
    );
  }

  Widget _provisionCard(Map<String, dynamic> provision) {
    final tier = firstNonEmpty([provision['relevance_tier'], 'Relevant']);
    final score = asDouble(provision['relevance_score']);
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 26,
                height: 26,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: AppColors.teal.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  '${asInt(provision['rank'], 1)}',
                  style: const TextStyle(
                    color: AppColors.teal,
                    fontWeight: FontWeight.w700,
                    fontSize: 12,
                  ),
                ),
              ),
              const SizedBox(width: 9),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${firstNonEmpty([provision['short_name'], provision['act_name'], 'Act'])} · Section ${firstNonEmpty([provision['section_number'], '—'])}',
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 13,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      firstNonEmpty([provision['section_title'], '']),
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.muted,
                      ),
                    ),
                  ],
                ),
              ),
              Tag(
                score > 0 ? '${score.toStringAsFixed(0)}' : tier,
                color: AppColors.info,
              ),
            ],
          ),
          const SizedBox(height: 9),
          if (asString(provision['simple_explanation']).isNotEmpty)
            Text(
              asString(provision['simple_explanation']),
              style: const TextStyle(fontSize: 12.5, height: 1.45),
            ),
          if (asString(provision['why_relevant']).isNotEmpty) ...[
            const SizedBox(height: 7),
            Text(
              'Why it applies: ${provision['why_relevant']}',
              style: const TextStyle(
                fontSize: 12,
                color: AppColors.muted,
                height: 1.4,
              ),
            ),
          ],
          if (asString(provision['snippet']).isNotEmpty) ...[
            const SizedBox(height: 9),
            ExpansionTile(
              tilePadding: EdgeInsets.zero,
              childrenPadding: const EdgeInsets.only(bottom: 4),
              shape: const Border(),
              title: const Text(
                'Statutory text',
                style: TextStyle(fontSize: 12),
              ),
              children: [
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    cleanLegalText(provision['snippet']),
                    style: const TextStyle(fontSize: 12, height: 1.5),
                  ),
                ),
              ],
            ),
          ],
          if (asString(provision['cautious_framing']).isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              asString(provision['cautious_framing']),
              style: const TextStyle(
                fontSize: 10.5,
                color: AppColors.muted,
                height: 1.35,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _actionPlan(Map<String, dynamic> actions) {
    List<Map<String, dynamic>> items(String key) => asMapList(actions[key]);
    final groups = {
      'Immediate actions': items('immediate_actions'),
      'Recommended next steps': items('recommended_next_steps'),
      'Optional supporting actions': items('optional_supporting_actions'),
    };
    final hasAny = groups.values.any((list) => list.isNotEmpty);
    if (!hasAny) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 8),
        const SectionTitle('Action plan'),
        for (final entry in groups.entries)
          if (entry.value.isNotEmpty) ...[
            Padding(
              padding: const EdgeInsets.only(bottom: 6, top: 4),
              child: Text(
                entry.key,
                style: const TextStyle(
                  fontWeight: FontWeight.w600,
                  fontSize: 13,
                ),
              ),
            ),
            for (final action in entry.value)
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
                              firstNonEmpty([action['action_title'], 'Action']),
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                                fontSize: 13,
                              ),
                            ),
                          ),
                          Tag(
                            firstNonEmpty([action['priority'], 'Normal']),
                            color: AppColors.warning,
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        asString(action['description']),
                        style: const TextStyle(fontSize: 12.5, height: 1.4),
                      ),
                      if (asString(action['statutory_basis']).isNotEmpty) ...[
                        const SizedBox(height: 5),
                        Text(
                          'Basis: ${action['statutory_basis']}',
                          style: const TextStyle(
                            fontSize: 11,
                            color: AppColors.teal,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
          ],
        if (asString(actions['guidance_note']).isNotEmpty)
          Text(
            asString(actions['guidance_note']),
            style: const TextStyle(
              fontSize: 11,
              color: AppColors.muted,
              height: 1.4,
            ),
          ),
      ],
    );
  }

  Widget _documentChecklist(Map<String, dynamic> documents) {
    List<Map<String, dynamic>> items(String key) => asMapList(documents[key]);
    final groups = {
      'Required documents': items('required_documents'),
      'Important documents': items('important_documents'),
      'Supporting documents': items('supporting_documents'),
    };
    if (!groups.values.any((list) => list.isNotEmpty) &&
        asString(documents['bsa_evidence_note']).isEmpty) {
      return const SizedBox.shrink();
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 8),
        const SectionTitle('Document & evidence checklist'),
        for (final entry in groups.entries)
          if (entry.value.isNotEmpty) ...[
            Padding(
              padding: const EdgeInsets.only(bottom: 6, top: 4),
              child: Text(
                entry.key,
                style: const TextStyle(
                  fontWeight: FontWeight.w600,
                  fontSize: 13,
                ),
              ),
            ),
            for (final doc in entry.value)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(
                            Icons.description_outlined,
                            size: 17,
                            color: AppColors.teal,
                          ),
                          const SizedBox(width: 7),
                          Expanded(
                            child: Text(
                              firstNonEmpty([doc['title'], 'Document']),
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                                fontSize: 13,
                              ),
                            ),
                          ),
                          if (asBool(doc['is_digital_evidence']))
                            const Tag('BSA 63', color: AppColors.info),
                        ],
                      ),
                      if (asString(doc['description']).isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(
                          asString(doc['description']),
                          style: const TextStyle(fontSize: 12.5, height: 1.4),
                        ),
                      ],
                      if (asString(doc['statutory_reference']).isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(
                          asString(doc['statutory_reference']),
                          style: const TextStyle(
                            fontSize: 11,
                            color: AppColors.teal,
                          ),
                        ),
                      ],
                      if (asString(doc['evidence_safeguard']).isNotEmpty) ...[
                        const SizedBox(height: 5),
                        Text(
                          asString(doc['evidence_safeguard']),
                          style: const TextStyle(
                            fontSize: 11,
                            color: AppColors.muted,
                            height: 1.4,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
          ],
        if (asString(documents['bsa_evidence_note']).isNotEmpty)
          Container(
            padding: const EdgeInsets.all(11),
            decoration: BoxDecoration(
              color: AppColors.info.withValues(alpha: 0.06),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              asString(documents['bsa_evidence_note']),
              style: const TextStyle(
                fontSize: 11,
                color: AppColors.muted,
                height: 1.4,
              ),
            ),
          ),
      ],
    );
  }

  Widget _procedure(Map<String, dynamic> procedure) {
    final steps = asMapList(procedure['procedural_pathway']);
    if (steps.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 8),
        const SectionTitle('Further procedure'),
        for (final step in steps)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: AppCard(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  CircleAvatar(
                    radius: 12,
                    backgroundColor: AppColors.navy,
                    child: Text(
                      '${asInt(step['step_number'], 1)}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 10.5,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          firstNonEmpty([step['stage_name'], 'Stage']),
                          style: const TextStyle(
                            fontWeight: FontWeight.w600,
                            fontSize: 13,
                          ),
                        ),
                        if (asString(step['authority_involved']).isNotEmpty)
                          Text(
                            asString(step['authority_involved']),
                            style: const TextStyle(
                              fontSize: 11.5,
                              color: AppColors.teal,
                            ),
                          ),
                        if (asString(step['description']).isNotEmpty) ...[
                          const SizedBox(height: 4),
                          Text(
                            asString(step['description']),
                            style: const TextStyle(fontSize: 12.5, height: 1.4),
                          ),
                        ],
                        if (asString(step['expected_timeline']).isNotEmpty) ...[
                          const SizedBox(height: 4),
                          Text(
                            'Timeline: ${step['expected_timeline']}',
                            style: const TextStyle(
                              fontSize: 11,
                              color: AppColors.muted,
                            ),
                          ),
                        ],
                        if (asMapList(step['safeguards']).isNotEmpty) ...[
                          const SizedBox(height: 6),
                          BulletList(
                            asMapList(step['safeguards'])
                                .map((e) => asString(e))
                                .where((e) => e.isNotEmpty)
                                .toList(),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        if (asString(procedure['procedural_note']).isNotEmpty)
          Text(
            asString(procedure['procedural_note']),
            style: const TextStyle(
              fontSize: 11,
              color: AppColors.muted,
              height: 1.4,
            ),
          ),
      ],
    );
  }
}

class _CaseIntakeForm extends StatefulWidget {
  const _CaseIntakeForm({required this.onAnalysed});

  final ValueChanged<Map<String, dynamic>> onAnalysed;

  @override
  State<_CaseIntakeForm> createState() => _CaseIntakeFormState();
}

class _CaseIntakeFormState extends State<_CaseIntakeForm> {
  final _description = TextEditingController();
  final _title = TextEditingController();
  final _type = TextEditingController();
  final _court = TextEditingController();
  final _location = TextEditingController();
  final _policeStation = TextEditingController();
  final _opposite = TextEditingController();
  final _incidentDate = TextEditingController();

  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _description.dispose();
    _title.dispose();
    _type.dispose();
    _court.dispose();
    _location.dispose();
    _policeStation.dispose();
    _opposite.dispose();
    _incidentDate.dispose();
    super.dispose();
  }

  Future<void> _analyse() async {
    if (_description.text.trim().length < 20) {
      setState(
        () => _error = 'Describe your situation in at least 20 characters so the analysis is grounded.',
      );
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final contextMap = await context.read<ApiService>().createAndAnalyzeCase({
        'title': _title.text.trim().isEmpty ? null : _title.text.trim(),
        'description': _description.text.trim(),
        'case_type': _type.text.trim().isEmpty ? null : _type.text.trim(),
        'court_name': _court.text.trim().isEmpty ? null : _court.text.trim(),
        'location': _location.text.trim().isEmpty
            ? null
            : _location.text.trim(),
        'police_station': _policeStation.text.trim().isEmpty
            ? null
            : _policeStation.text.trim(),
        'opposite_party': _opposite.text.trim().isEmpty
            ? null
            : _opposite.text.trim(),
        'incident_date': _incidentDate.text.trim().isEmpty
            ? null
            : _incidentDate.text.trim(),
      });
      if (!mounted) return;
      widget.onAnalysed(contextMap);
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
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
      children: [
        const AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.psychology_alt_outlined, color: AppColors.teal),
                  SizedBox(width: 8),
                  Text(
                    'Describe what happened',
                    style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                  ),
                ],
              ),
              SizedBox(height: 8),
              Text(
                'Case Intelligence extracts facts, retrieves potentially applicable provisions and builds a document and procedural plan. '
                'It does not decide guilt or liability.',
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
        TextField(
          controller: _description,
          minLines: 5,
          maxLines: 10,
          textCapitalization: TextCapitalization.sentences,
          decoration: const InputDecoration(
            labelText: 'Your situation *',
            hintText: 'For example: On 2 March my landlord refused to return my ₹50,000 security deposit after I vacated the flat in Pune…',
            alignLabelWithHint: true,
          ),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _title,
          textCapitalization: TextCapitalization.sentences,
          decoration: const InputDecoration(
            labelText: 'Short title (optional)',
          ),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _type,
          decoration: const InputDecoration(labelText: 'Case type (optional)'),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _location,
          decoration: const InputDecoration(
            labelText: 'Location / city (optional)',
            prefixIcon: Icon(Icons.place_outlined),
          ),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _policeStation,
          decoration: const InputDecoration(
            labelText: 'Police station (optional)',
          ),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _court,
          decoration: const InputDecoration(labelText: 'Court (optional)'),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _opposite,
          decoration: const InputDecoration(
            labelText: 'Opposite party (optional)',
          ),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _incidentDate,
          decoration: const InputDecoration(
            labelText: 'Incident date (optional)',
            hintText: 'YYYY-MM-DD',
          ),
        ),
        const SizedBox(height: 16),
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
              : const Icon(Icons.auto_awesome),
          label: Text(_busy ? 'Analysing…' : 'Analyse my situation'),
        ),
        const SizedBox(height: 8),
        const Text(
          'Do not include passwords, OTPs or unnecessary identity numbers.',
          style: TextStyle(fontSize: 11, color: AppColors.muted),
        ),
      ],
    );
  }
}

class _AdditionalFactsSheet extends StatefulWidget {
  const _AdditionalFactsSheet({required this.caseId});

  final int caseId;

  @override
  State<_AdditionalFactsSheet> createState() => _AdditionalFactsSheetState();
}

class _AdditionalFactsSheetState extends State<_AdditionalFactsSheet> {
  final _facts = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _facts.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_facts.text.trim().length < 5) {
      setState(() {
        _error = 'Add at least a short sentence of new information.';
      });
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final updated = await context.read<ApiService>().updateAndReanalyzeCase(
        widget.caseId,
        _facts.text.trim(),
      );
      if (!mounted) return;
      Navigator.of(context).pop(updated);
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
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Add new information',
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 4),
              const Text(
                'The case will be re-analysed against the statutory corpus with these facts included.',
                style: TextStyle(
                  fontSize: 11.5,
                  color: AppColors.muted,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 12),
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
              TextField(
                controller: _facts,
                minLines: 4,
                maxLines: 8,
                textCapitalization: TextCapitalization.sentences,
                decoration: const InputDecoration(
                  labelText: 'Additional facts',
                  alignLabelWithHint: true,
                ),
              ),
              const SizedBox(height: 14),
              FilledButton(
                onPressed: _busy ? null : _submit,
                child: _busy
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2.2,
                          color: Colors.white,
                        ),
                      )
                    : const Text('Re-analyse case'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
