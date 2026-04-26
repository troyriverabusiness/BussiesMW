import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import {
  LegalDataHubSource,
  LegalSourceListComponent,
} from '../legal-source-list/legal-source-list.component';
import { TraceJsonViewerComponent } from '../trace-json-viewer/trace-json-viewer.component';

type LegalCaseStatus = 'Open' | 'Closed' | 'Action Required' | 'Awaiting Counterparty' | 'Awaiting Internal';
type PriorityRiskLevel = 'Low' | 'Medium' | 'High' | 'Critical';
type WorkspaceSection = 'overview' | 'traceability';

interface LegalCaseDetail {
  id: string;
  title?: string | null;
  department?: string | null;
  status: LegalCaseStatus;
  priority: PriorityRiskLevel;
  nextDueDate?: string | null;
  internal: boolean;
  plaintiff?: string | null;
  defendant?: string | null;
  courtAuthority?: string | null;
  jurisdiction?: string | null;
  claimAmount?: number | null;
  legalIssue?: string | null;
  caseFacts?: string[] | null;
  informationGaps?: string[] | null;
  suggestionActionItems?: string[] | null;
  lastUpdateDate: string;
  sourceDocuments?: string | null;
  caseSummary?: string | null;
}

interface ChatMessage {
  role: 'assistant' | 'user';
  text: string;
  status?: ChatMessageStatus;
  activities?: ChatActivity[];
  createdAt?: string;
}

interface ChatHistoryMessage {
  role: 'assistant' | 'user';
  content: string;
}

interface ChatSession {
  id: string;
  caseId: string;
  userId?: string | null;
  title: string;
  createdAt: string;
  updatedAt: string;
}

interface PersistedChatMessage {
  id: string;
  sessionId: string;
  role: 'assistant' | 'user';
  content: string;
  toolCalls?: unknown;
  toolResults?: unknown;
  createdAt: string;
}

interface PersistedToolCall {
  name: string;
  args?: Record<string, unknown>;
}

interface PersistedToolResult {
  name: string;
  result?: unknown;
}

type ChatMessageStatus = 'thinking' | 'using-tools' | 'responding' | 'complete' | 'error';

interface ChatActivity {
  name: string;
  args?: Record<string, unknown>;
  result?: unknown;
  status: 'running' | 'completed' | 'approval-required' | 'denied';
}

interface ApprovedToolCall {
  name: string;
  args: Record<string, unknown>;
}

interface ChatStreamEvent {
  session?: {
    id: string;
  };
  content?: string;
  tool_call?: {
    name: string;
    args: Record<string, unknown>;
  };
  tool_result?: {
    name: string;
    result?: unknown;
  };
  approval_required?: {
    name: string;
    args: Record<string, unknown>;
  };
  error?: string;
}

interface TraceStep {
  id: string;
  traceId: string;
  step: string;
  input: unknown;
  output: unknown;
  reasoning: string;
  confidence: number;
  toolCalls: unknown;
  createdAt: string;
}

interface HumanReview {
  id: string;
  traceId: string;
  traceStepId?: string | null;
  reviewerName: string;
  decision: string;
  comment: string;
  reviewedAt: string;
}

interface Trace {
  id: string;
  caseId?: string | null;
  startedAt?: string | null;
  completedAt?: string | null;
  traceSteps: TraceStep[];
  reviews?: HumanReview[];
}

@Component({
  selector: 'app-case-workspace',
  imports: [CommonModule, CurrencyPipe, DatePipe, RouterLink, TraceJsonViewerComponent, LegalSourceListComponent],
  templateUrl: './case-workspace.html',
  styleUrl: './case-workspace.scss',
})
export class CaseWorkspaceComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly caseId = this.route.snapshot.paramMap.get('id') ?? '';
  private readonly caseApiUrl = `${this.apiOrigin}/api/v1/cases/${this.caseId}`;
  private readonly traceabilityApiUrl = `${this.apiOrigin}/api/v1/cases/${this.caseId}/traces`;
  private readonly chatApiUrl = `${this.apiOrigin}/api/v1/chat`;
  private readonly chatSessionsApiUrl = `${this.apiOrigin}/api/v1/cases/${this.caseId}/chat-sessions`;
  private readonly reviewsApiUrl = `${this.apiOrigin}/api/v1/reviews`;

  readonly legalCase = signal<LegalCaseDetail | null>(null);
  readonly isLoading = signal(true);
  readonly errorMessage = signal('');
  readonly activeSection = signal<WorkspaceSection>('overview');
  readonly sidebarCollapsed = signal(false);
  readonly overviewHidden = signal(false);
  readonly chatDraft = signal('');
  readonly chatLoading = signal(false);
  readonly messages = signal<ChatMessage[]>([]);
  readonly chatSessions = signal<ChatSession[]>([]);
  readonly activeChatSessionId = signal<string | null>(null);
  readonly chatSessionsLoading = signal(false);
  readonly chatMessagesLoading = signal(false);
  readonly chatSessionsError = signal('');
  readonly traceability = signal<Trace[] | null>(null);
  readonly traceabilityLoading = signal(false);
  readonly traceabilityError = signal('');
  readonly expandedTraceIds = signal<Set<string>>(new Set());
  readonly sourceDocumentsOpen = signal(false);
  readonly selectedReviewTrace = signal<Trace | null>(null);
  readonly selectedReviewStep = signal<TraceStep | null>(null);
  readonly reviewDecision = signal('Approve');
  readonly reviewComment = signal('');
  readonly reviewSaving = signal(false);
  readonly metadata = computed(() => {
    const legalCase = this.legalCase();
    if (!legalCase) {
      return [];
    }

    return [
      { label: 'Title', value: this.caseTitle(legalCase) },
      { label: 'Department', value: legalCase.department || 'Unassigned' },
      { label: 'Status', value: legalCase.status },
      { label: 'Priority/risk level', value: legalCase.priority },
      { label: 'Last updated date', value: legalCase.lastUpdateDate, type: 'date' },
      { label: 'Next due date', value: legalCase.nextDueDate, type: 'date' },
      { label: 'Internal matter', value: legalCase.internal ? 'Yes' : 'No' },
      { label: 'Plaintiff', value: legalCase.plaintiff || 'Not specified' },
      { label: 'Defendant', value: legalCase.defendant || 'Not specified' },
      { label: 'Court authority', value: legalCase.courtAuthority || 'Not specified' },
      { label: 'Jurisdiction', value: legalCase.jurisdiction || 'Not specified' },
      { label: 'Claim amount', value: legalCase.claimAmount, type: 'currency' },
      { label: 'Source documents', value: legalCase.sourceDocuments || 'Not specified' },
    ].filter((item) => item.value !== null && item.value !== undefined && item.value !== '');
  });

  ngOnInit(): void {
    this.loadChatSessions();
    this.http
      .get<LegalCaseDetail>(this.caseApiUrl)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: (legalCase) => {
          this.legalCase.set(legalCase);
        },
        error: () => this.errorMessage.set('This case could not be loaded. Return to the dashboard and try again.'),
      });
  }

  toggleSidebar(): void {
    this.sidebarCollapsed.update((isCollapsed) => !isCollapsed);
  }

  setSection(section: WorkspaceSection): void {
    this.activeSection.set(section);
    if (section === 'traceability') {
      this.loadTraceability();
    }
  }

  hideOverview(): void {
    this.overviewHidden.set(true);
  }

  restoreOverview(): void {
    this.overviewHidden.set(false);
  }

  toggleSourceDocuments(): void {
    this.sourceDocumentsOpen.update((isOpen) => !isOpen);
  }

  setChatDraft(message: string): void {
    this.chatDraft.set(message);
  }

  startNewChatSession(): void {
    if (this.chatSessionsLoading() || this.chatMessagesLoading() || this.chatLoading()) {
      return;
    }

    this.chatSessionsLoading.set(true);
    this.chatSessionsError.set('');
    this.http
      .post<ChatSession>(this.chatSessionsApiUrl, {})
      .pipe(finalize(() => this.chatSessionsLoading.set(false)))
      .subscribe({
        next: (session) => {
          this.chatSessions.update((sessions) => [session, ...sessions.filter((item) => item.id !== session.id)]);
          this.activeChatSessionId.set(session.id);
          this.messages.set([]);
        },
        error: () => this.chatSessionsError.set('Chat session could not be created.'),
      });
  }

  selectChatSession(session: ChatSession): void {
    if (this.chatMessagesLoading() || this.activeChatSessionId() === session.id) {
      return;
    }

    this.activeChatSessionId.set(session.id);
    this.chatMessagesLoading.set(true);
    this.chatSessionsError.set('');
    this.http
      .get<PersistedChatMessage[]>(this.chatSessionMessagesApiUrl(session.id))
      .pipe(finalize(() => this.chatMessagesLoading.set(false)))
      .subscribe({
        next: (messages) => {
          this.messages.set(
            messages.map((message) => {
              const activities = this.persistedToolActivities(message);
              return {
                role: message.role,
                text: message.content,
                createdAt: message.createdAt,
                status: message.role === 'assistant' ? 'complete' : undefined,
                activities: activities.length ? activities : undefined,
              };
            }),
          );
        },
        error: () => this.chatSessionsError.set('Chat messages could not be loaded.'),
      });
  }

  async sendChatMessage(event: Event): Promise<void> {
    event.preventDefault();
    const message = this.chatDraft().trim();
    if (!message || this.chatLoading() || this.chatMessagesLoading()) {
      return;
    }

    const history = this.toChatHistory();
    const sessionId = this.activeChatSessionId();
    this.chatDraft.set('');
    this.chatLoading.set(true);
    this.appendMessage({ role: 'user', text: message });
    this.appendMessage({ role: 'assistant', text: '', status: 'thinking', activities: [] });

    try {
      await this.streamChatResponse({
        message,
        caseId: this.caseId,
        sessionId,
        messages: history,
      });
      this.ensureAssistantMessageText('Veritas did not return a response.');
      this.setLastAssistantStatus('complete');
      this.loadChatSessions({ preserveActiveSession: true });
    } catch (error) {
      this.replaceLastAssistantMessage(this.chatFailureMessage(error));
      this.setLastAssistantStatus('error');
    } finally {
      this.chatLoading.set(false);
    }
  }

  async approveExternalContact(activity: ChatActivity): Promise<void> {
    if (this.chatLoading() || this.chatMessagesLoading()) {
      return;
    }

    this.markActivityStatus(activity, 'completed');
    const history = this.toChatHistory();
    const sessionId = this.activeChatSessionId();
    const message = 'Approved external contact.';
    this.chatLoading.set(true);
    this.appendMessage({ role: 'user', text: message });
    this.appendMessage({ role: 'assistant', text: '', status: 'thinking', activities: [] });

    try {
      await this.streamChatResponse({
        message,
        caseId: this.caseId,
        sessionId,
        messages: history,
        approvedToolCall: { name: activity.name, args: activity.args ?? {} },
      });
      this.ensureAssistantMessageText('Veritas did not return a response.');
      this.setLastAssistantStatus('complete');
      this.loadChatSessions({ preserveActiveSession: true });
    } catch (error) {
      this.replaceLastAssistantMessage(this.chatFailureMessage(error));
      this.setLastAssistantStatus('error');
    } finally {
      this.chatLoading.set(false);
    }
  }

  denyExternalContact(activity: ChatActivity): void {
    if (this.chatLoading() || this.chatMessagesLoading()) {
      return;
    }

    this.markActivityStatus(activity, 'denied');
    this.appendMessage({ role: 'user', text: 'Denied external contact.' });
    this.appendMessage({
      role: 'assistant',
      text: 'External contact was not sent.',
      status: 'complete',
      activities: [],
    });
  }

  toggleTrace(traceId: string): void {
    this.expandedTraceIds.update((traceIds) => {
      const nextTraceIds = new Set(traceIds);
      if (nextTraceIds.has(traceId)) {
        nextTraceIds.delete(traceId);
      } else {
        nextTraceIds.add(traceId);
      }
      return nextTraceIds;
    });
  }

  isTraceExpanded(traceId: string): boolean {
    return this.expandedTraceIds().has(traceId);
  }

  openReview(trace: Trace, step?: TraceStep): void {
    this.selectedReviewTrace.set(trace);
    this.selectedReviewStep.set(step ?? trace.traceSteps.find((traceStep) => this.stepRequiresReview(traceStep)) ?? null);
    this.reviewDecision.set('Approve');
    this.reviewComment.set('');
  }

  closeReview(): void {
    this.selectedReviewTrace.set(null);
    this.selectedReviewStep.set(null);
  }

  setReviewDecision(decision: string): void {
    this.reviewDecision.set(decision);
  }

  setReviewComment(comment: string): void {
    this.reviewComment.set(comment);
  }

  submitReview(event: Event): void {
    event.preventDefault();
    const trace = this.selectedReviewTrace();
    if (!trace || this.reviewSaving()) {
      return;
    }

    this.reviewSaving.set(true);
    this.http
      .post<HumanReview>(this.reviewsApiUrl, {
        traceId: trace.id,
        traceStepId: this.selectedReviewStep()?.id ?? null,
        reviewerName: 'Legal reviewer',
        decision: this.reviewDecision(),
        comment: this.reviewComment().trim() || 'Reviewed in the traceability workspace.',
      })
      .pipe(finalize(() => this.reviewSaving.set(false)))
      .subscribe({
        next: (review) => {
          this.traceability.update((traceability) => {
            if (!traceability) {
              return traceability;
            }
            return traceability.map((item) =>
              item.id === trace.id ? { ...item, reviews: [...(item.reviews ?? []), review] } : item,
            );
          });
          this.closeReview();
        },
      });
  }

  riskClass(riskLevel: PriorityRiskLevel): string {
    return riskLevel.toLowerCase();
  }

  statusClass(status: LegalCaseStatus): string {
    return status.toLowerCase().replace(/\s+/g, '-');
  }

  traceStatusClass(status: string): string {
    return status.toLowerCase().replace(/\s+/g, '-');
  }

  formatPercent(value: number): string {
    return `${Math.round(value * 100)}%`;
  }

  caseTitle(legalCase: LegalCaseDetail): string {
    return legalCase.title || legalCase.legalIssue || 'Untitled legal case';
  }

  caseTags(legalCase: LegalCaseDetail): string[] {
    return [
      legalCase.department,
      legalCase.internal ? 'Internal' : 'External',
      legalCase.jurisdiction,
      `${legalCase.priority} priority`,
    ].filter((tag): tag is string => Boolean(tag));
  }

  partiesSummary(legalCase: LegalCaseDetail): string {
    return [legalCase.plaintiff, legalCase.defendant].filter(Boolean).join(' vs ') || 'Parties not specified';
  }

  nextActionSummary(legalCase: LegalCaseDetail): string {
    return legalCase.suggestionActionItems?.[0] || legalCase.informationGaps?.[0] || 'No next action recorded';
  }

  traceStatus(trace: Trace): string {
    return trace.completedAt ? 'Completed' : 'In progress';
  }

  traceTimestamp(trace: Trace): string | null {
    return trace.startedAt || trace.completedAt || null;
  }

  traceConfidence(trace: Trace): number {
    if (!trace.traceSteps.length) {
      return 0;
    }

    const totalConfidence = trace.traceSteps.reduce((total, step) => total + step.confidence, 0);
    return totalConfidence / trace.traceSteps.length;
  }

  traceRequiresReview(trace: Trace): boolean {
    return trace.traceSteps.some((step) => this.stepRequiresReview(step));
  }

  stepRequiresReview(step: TraceStep): boolean {
    return step.confidence < 0.75;
  }

  assistantStatusLabel(message: ChatMessage): string {
    if (message.role !== 'assistant') {
      return '';
    }

    if (message.status === 'using-tools') {
      return 'Using workspace tools';
    }
    if (message.status === 'responding') {
      return 'Streaming response';
    }
    if (message.status === 'error') {
      return 'Response interrupted';
    }
    if (message.status === 'thinking') {
      return 'Reviewing case context';
    }
    return message.activities?.length ? 'Workspace context checked' : '';
  }

  assistantStatusIcon(message: ChatMessage): string {
    if (message.status === 'complete') {
      return 'check_circle';
    }
    if (message.status === 'error') {
      return 'error';
    }
    return 'progress_activity';
  }

  isAssistantStatusLive(message: ChatMessage): boolean {
    return (
      message.status === 'thinking' ||
      message.status === 'using-tools' ||
      message.status === 'responding'
    );
  }

  shouldShowThinking(message: ChatMessage): boolean {
    return (
      message.status === 'thinking' ||
      message.status === 'using-tools' ||
      message.status === 'responding' ||
      message.status === 'error'
    );
  }

  thinkingStatusLabel(message: ChatMessage): string {
    if (message.status === 'responding') {
      return 'Writing response';
    }
    if (message.status === 'error') {
      return 'Response interrupted';
    }
    return 'Thinking';
  }

  toolCallStatusLabel(activity: ChatActivity): string {
    if (activity.name === 'legal_data_hub_search') {
      return activity.status === 'running' ? 'Calling Legal Data Hub...' : 'Legal Data Hub research complete';
    }

    const actions: Record<ChatActivity['status'], string> = {
      running: 'Calling tool',
      completed: 'Called tool',
      'approval-required': 'Approval required',
      denied: 'Denied',
    };
    const action = actions[activity.status];
    return `${action}: ${this.activityLabel(activity)}`;
  }

  activityLabel(activity: ChatActivity): string {
    const labels: Record<string, string> = {
      list_cases: 'List cases',
      get_case: 'Case lookup',
      list_case_traces: 'Trace lookup',
      legal_data_hub_search: 'Legal Data Hub',
      contact_internal_employee: 'Contact internal employee',
      contact_external_person: 'Contact external person',
    };
    return labels[activity.name] ?? this.toTitleCase(activity.name.replace(/^get_/, '').replace(/_/g, ' '));
  }

  activityIcon(activity: ChatActivity): string {
    const icons: Record<string, string> = {
      list_cases: 'folder_open',
      get_case: 'clinical_notes',
      list_case_traces: 'timeline',
      legal_data_hub_search: 'policy',
      contact_internal_employee: 'mail',
      contact_external_person: 'outgoing_mail',
    };
    return icons[activity.name] ?? 'construction';
  }

  approvalPreview(activity: ChatActivity): string {
    const message = activity.args?.['message'];
    return typeof message === 'string' ? message : '';
  }

  renderMessageText(text: string): string {
    return this.markdownToHtml(text);
  }

  chatSessionTitle(session: ChatSession): string {
    return session.title || 'New chat';
  }

  chatSessionTimestamp(session: ChatSession): string {
    return session.updatedAt || session.createdAt;
  }

  legalDataHubSources(message: ChatMessage): LegalDataHubSource[] {
    const activity = message.activities?.find(
      (item) => item.name === 'legal_data_hub_search' && item.status === 'completed',
    );
    const result = this.isRecord(activity?.result) ? activity.result : null;
    const sources = result?.['sources'];
    if (!Array.isArray(sources)) {
      return [];
    }

    return sources.flatMap((source) => {
      if (!this.isRecord(source)) {
        return [];
      }
      return [
        {
          title: this.sourceText(source, 'title') || 'Legal Data Hub source',
          court: this.sourceText(source, 'court'),
          date: this.sourceText(source, 'date'),
          ecli: this.sourceText(source, 'ecli'),
          aktenzeichen: this.sourceText(source, 'aktenzeichen'),
          document_type: this.sourceText(source, 'document_type'),
          relevance_score: this.sourceScore(source['relevance_score']),
          excerpt: this.sourceText(source, 'excerpt'),
          why_used: this.sourceText(source, 'why_used'),
        },
      ];
    });
  }

  private loadChatSessions(options: { preserveActiveSession?: boolean } = {}): void {
    this.chatSessionsLoading.set(true);
    this.chatSessionsError.set('');
    this.http
      .get<ChatSession[]>(this.chatSessionsApiUrl)
      .pipe(finalize(() => this.chatSessionsLoading.set(false)))
      .subscribe({
        next: (sessions) => {
          this.chatSessions.set(sessions);
          const activeSessionId = this.activeChatSessionId();
          if (options.preserveActiveSession && activeSessionId) {
            return;
          }
          const firstSession = sessions[0];
          if (firstSession) {
            this.selectChatSession(firstSession);
          }
        },
        error: () => this.chatSessionsError.set('Chat history could not be loaded.'),
      });
  }

  private loadTraceability(): void {
    if (this.traceability() || this.traceabilityLoading()) {
      return;
    }

    this.traceabilityLoading.set(true);
    this.traceabilityError.set('');
    this.http
      .get<Trace[]>(this.traceabilityApiUrl)
      .pipe(finalize(() => this.traceabilityLoading.set(false)))
      .subscribe({
        next: (traceability) => {
          this.traceability.set(traceability);
          this.expandedTraceIds.set(new Set(traceability.slice(0, 1).map((trace) => trace.id)));
        },
        error: () => this.traceabilityError.set('Traceability data could not be loaded for this case.'),
      });
  }

  private appendMessage(message: ChatMessage): void {
    this.messages.update((messages) => [...messages, message]);
  }

  private async streamChatResponse(payload: {
    message: string;
    caseId: string;
    sessionId: string | null;
    messages: ChatHistoryMessage[];
    approvedToolCall?: ApprovedToolCall;
  }): Promise<void> {
    const response = await fetch(this.chatApiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok || !response.body) {
      throw new Error('Chat stream failed.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });

      let separatorIndex = buffer.indexOf('\n\n');
      while (separatorIndex !== -1) {
        const rawEvent = buffer.slice(0, separatorIndex).trim();
        buffer = buffer.slice(separatorIndex + 2);
        this.handleChatStreamEvent(rawEvent);
        separatorIndex = buffer.indexOf('\n\n');
      }

      if (done) {
        break;
      }
    }
  }

  private handleChatStreamEvent(rawEvent: string): void {
    const dataLine = rawEvent
      .split('\n')
      .find((line) => line.startsWith('data:'));
    const rawData = dataLine?.replace(/^data:\s*/, '');
    if (!rawData || rawData === '[DONE]') {
      return;
    }

    const streamEvent = JSON.parse(rawData) as ChatStreamEvent;
    if (streamEvent.error) {
      throw new Error(streamEvent.error);
    }
    if (streamEvent.session) {
      this.activeChatSessionId.set(streamEvent.session.id);
    }
    if (streamEvent.tool_call) {
      this.recordToolCall(streamEvent.tool_call);
    }
    if (streamEvent.tool_result) {
      this.completeToolCall(streamEvent.tool_result.name, streamEvent.tool_result.result);
    }
    if (streamEvent.approval_required) {
      this.markApprovalRequired(streamEvent.approval_required);
    }
    if (streamEvent.content) {
      this.setLastAssistantStatus('responding');
      this.appendToLastAssistantMessage(streamEvent.content);
    }
  }

  private appendToLastAssistantMessage(content: string): void {
    this.updateLastAssistantMessage((message) => `${message}${content}`);
  }

  private replaceLastAssistantMessage(text: string): void {
    this.updateLastAssistantMessage(() => text);
  }

  private recordToolCall(toolCall: { name: string; args: Record<string, unknown> }): void {
    this.messages.update((messages) => {
      const nextMessages = [...messages];
      const lastMessage = nextMessages.at(-1);
      if (lastMessage?.role === 'assistant') {
        nextMessages[nextMessages.length - 1] = {
          ...lastMessage,
          status: 'using-tools',
          activities: [
            ...(lastMessage.activities ?? []),
            { name: toolCall.name, args: toolCall.args, status: 'running' },
          ],
        };
      }
      return nextMessages;
    });
  }

  private completeToolCall(toolName: string, result?: unknown): void {
    this.messages.update((messages) => {
      const nextMessages = [...messages];
      const lastMessage = nextMessages.at(-1);
      if (lastMessage?.role === 'assistant') {
        nextMessages[nextMessages.length - 1] = {
          ...lastMessage,
          status: lastMessage.text.trim() ? 'responding' : 'using-tools',
          activities: (lastMessage.activities ?? []).map((activity) =>
            activity.name === toolName ? { ...activity, result, status: 'completed' } : activity,
          ),
        };
      }
      return nextMessages;
    });
  }

  private markApprovalRequired(toolCall: { name: string; args: Record<string, unknown> }): void {
    this.messages.update((messages) => {
      const nextMessages = [...messages];
      const lastMessage = nextMessages.at(-1);
      if (lastMessage?.role === 'assistant') {
        nextMessages[nextMessages.length - 1] = {
          ...lastMessage,
          status: 'using-tools',
          activities: (lastMessage.activities ?? []).map((activity) =>
            activity.name === toolCall.name ? { ...activity, status: 'approval-required' } : activity,
          ),
        };
      }
      return nextMessages;
    });
  }

  private markActivityStatus(activityToUpdate: ChatActivity, status: ChatActivity['status']): void {
    this.messages.update((messages) =>
      messages.map((message) => ({
        ...message,
        activities: message.activities?.map((activity) =>
          activity === activityToUpdate ||
          (activity.name === activityToUpdate.name &&
            JSON.stringify(activity.args ?? {}) === JSON.stringify(activityToUpdate.args ?? {}))
            ? { ...activity, status }
            : activity,
        ),
      })),
    );
  }

  private setLastAssistantStatus(status: ChatMessageStatus): void {
    this.messages.update((messages) => {
      const nextMessages = [...messages];
      const lastMessage = nextMessages.at(-1);
      if (lastMessage?.role === 'assistant') {
        nextMessages[nextMessages.length - 1] = { ...lastMessage, status };
      }
      return nextMessages;
    });
  }

  private ensureAssistantMessageText(fallback: string): void {
    const lastMessage = this.messages().at(-1);
    if (lastMessage?.role === 'assistant' && !lastMessage.text.trim()) {
      this.replaceLastAssistantMessage(fallback);
    }
  }

  private chatFailureMessage(error: unknown): string {
    const detail = error instanceof Error ? error.message.trim() : '';
    return detail
      ? `Veritas could not reach the AI chat service. Server error: ${detail}`
      : 'Veritas could not reach the AI chat service. Please try again.';
  }

  private updateLastAssistantMessage(updateText: (currentText: string) => string): void {
    this.messages.update((messages) => {
      const nextMessages = [...messages];
      const lastMessage = nextMessages.at(-1);
      if (lastMessage?.role === 'assistant') {
        nextMessages[nextMessages.length - 1] = {
          ...lastMessage,
          text: updateText(lastMessage.text),
        };
      }
      return nextMessages;
    });
  }

  private persistedToolActivities(message: PersistedChatMessage): ChatActivity[] {
    if (message.role !== 'assistant') {
      return [];
    }

    const toolCalls = this.asPersistedToolCalls(message.toolCalls);
    if (!toolCalls.length) {
      return [];
    }

    const completedToolResults = new Map(
      this.asPersistedToolResults(message.toolResults).map((result) => [result.name, result.result]),
    );
    return toolCalls.map((toolCall) => ({
      name: toolCall.name,
      args: toolCall.args,
      result: completedToolResults.get(toolCall.name),
      status: !completedToolResults.size || completedToolResults.has(toolCall.name) ? 'completed' : 'running',
    }));
  }

  private asPersistedToolCalls(value: unknown): PersistedToolCall[] {
    if (!Array.isArray(value)) {
      return [];
    }

    return value.flatMap((item) => {
      if (!this.isRecord(item) || typeof item['name'] !== 'string') {
        return [];
      }
      const args = this.isRecord(item['args']) ? item['args'] : undefined;
      return [{ name: item['name'], args }];
    });
  }

  private asPersistedToolResults(value: unknown): PersistedToolResult[] {
    if (!Array.isArray(value)) {
      return [];
    }

    return value.flatMap((item) => {
      if (!this.isRecord(item) || typeof item['name'] !== 'string') {
        return [];
      }
      return [{ name: item['name'], result: item['result'] }];
    });
  }

  private isRecord(value: unknown): value is Record<string, unknown> {
    return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
  }

  private sourceText(record: Record<string, unknown>, key: string): string {
    const value = record[key];
    return typeof value === 'string' ? value : '';
  }

  private sourceScore(value: unknown): number | undefined {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === 'string') {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : undefined;
    }
    return undefined;
  }

  private toTitleCase(value: string): string {
    return value.replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  private markdownToHtml(source: string): string {
    const lines = source.trim().split(/\r?\n/);
    const blocks: string[] = [];
    let paragraphLines: string[] = [];
    let listItems: string[] = [];

    const flushParagraph = () => {
      if (!paragraphLines.length) {
        return;
      }
      blocks.push(`<p>${this.inlineMarkdown(paragraphLines.join(' '))}</p>`);
      paragraphLines = [];
    };

    const flushList = () => {
      if (!listItems.length) {
        return;
      }
      blocks.push(`<ul>${listItems.join('')}</ul>`);
      listItems = [];
    };

    for (const line of lines) {
      const trimmedLine = line.trim();
      if (!trimmedLine) {
        flushParagraph();
        flushList();
        continue;
      }

      const bulletMatch = trimmedLine.match(/^[-*]\s+(.+)$/);
      if (bulletMatch) {
        flushParagraph();
        listItems.push(`<li>${this.inlineMarkdown(bulletMatch[1])}</li>`);
        continue;
      }

      flushList();
      paragraphLines.push(trimmedLine);
    }

    flushParagraph();
    flushList();
    return blocks.join('');
  }

  private inlineMarkdown(source: string): string {
    return this.escapeHtml(source).replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  }

  private escapeHtml(source: string): string {
    return source
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  private toChatHistory(): ChatHistoryMessage[] {
    return this.messages()
      .filter((message) => message.text.trim())
      .map((message) => ({ role: message.role, content: message.text }));
  }

  private get apiOrigin(): string {
    const hostname = window.location.hostname || 'localhost';
    return `http://${hostname}:8000`;
  }

  private chatSessionMessagesApiUrl(sessionId: string): string {
    return `${this.apiOrigin}/api/v1/chat-sessions/${sessionId}/messages`;
  }
}
