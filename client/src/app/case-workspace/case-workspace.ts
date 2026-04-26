import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

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
}

interface ChatHistoryMessage {
  role: 'assistant' | 'user';
  content: string;
}

interface ChatStreamEvent {
  content?: string;
  tool_call?: {
    name: string;
    args: Record<string, unknown>;
  };
  tool_result?: {
    name: string;
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
  imports: [CommonModule, CurrencyPipe, DatePipe, RouterLink],
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
  readonly traceability = signal<Trace[] | null>(null);
  readonly traceabilityLoading = signal(false);
  readonly traceabilityError = signal('');
  readonly expandedTraceIds = signal<Set<string>>(new Set());
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

  setChatDraft(message: string): void {
    this.chatDraft.set(message);
  }

  async sendChatMessage(event: Event): Promise<void> {
    event.preventDefault();
    const message = this.chatDraft().trim();
    if (!message || this.chatLoading()) {
      return;
    }

    const history = this.toChatHistory();
    this.chatDraft.set('');
    this.chatLoading.set(true);
    this.appendMessage({ role: 'user', text: message });
    this.appendMessage({ role: 'assistant', text: '' });

    try {
      await this.streamChatResponse({
        message,
        caseId: this.caseId,
        messages: history,
      });
      this.ensureAssistantMessageText('Toto did not return a response.');
    } catch (error) {
      this.replaceLastAssistantMessage(this.chatFailureMessage(error));
    } finally {
      this.chatLoading.set(false);
    }
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
    messages: ChatHistoryMessage[];
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
    if (streamEvent.content) {
      this.appendToLastAssistantMessage(streamEvent.content);
    }
  }

  private appendToLastAssistantMessage(content: string): void {
    this.updateLastAssistantMessage((message) => `${message}${content}`);
  }

  private replaceLastAssistantMessage(text: string): void {
    this.updateLastAssistantMessage(() => text);
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
      ? `Toto could not reach the AI chat service. Server error: ${detail}`
      : 'Toto could not reach the AI chat service. Please try again.';
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

  private toChatHistory(): ChatHistoryMessage[] {
    return this.messages()
      .filter((message) => message.text.trim())
      .map((message) => ({ role: message.role, content: message.text }));
  }

  private get apiOrigin(): string {
    const hostname = window.location.hostname || 'localhost';
    return `http://${hostname}:8000`;
  }
}
