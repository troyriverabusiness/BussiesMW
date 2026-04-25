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

interface TotoChatResponse {
  status: string;
  lastCorrespondence: string;
  waitingFor: string;
  summary: string;
}

interface ChatMessage {
  role: 'assistant' | 'user';
  text: string;
  response?: TotoChatResponse;
}

interface ChatConversation {
  id: string;
  title: string;
  subtitle: string;
  updatedAt: string;
  messages: ChatMessage[];
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
  private readonly totoApiUrl = `${this.apiOrigin}/api/v1/toto/chat`;
  private readonly reviewsApiUrl = `${this.apiOrigin}/api/v1/reviews`;

  readonly legalCase = signal<LegalCaseDetail | null>(null);
  readonly isLoading = signal(true);
  readonly errorMessage = signal('');
  readonly activeSection = signal<WorkspaceSection>('overview');
  readonly sidebarCollapsed = signal(false);
  readonly overviewHidden = signal(false);
  readonly totoDraft = signal('');
  readonly totoLoading = signal(false);
  readonly conversations = signal<ChatConversation[]>([]);
  readonly activeConversationId = signal('');
  readonly traceability = signal<Trace[] | null>(null);
  readonly traceabilityLoading = signal(false);
  readonly traceabilityError = signal('');
  readonly expandedTraceIds = signal<Set<string>>(new Set());
  readonly selectedReviewTrace = signal<Trace | null>(null);
  readonly selectedReviewStep = signal<TraceStep | null>(null);
  readonly reviewDecision = signal('Approve');
  readonly reviewComment = signal('');
  readonly reviewSaving = signal(false);
  readonly messages = computed(() => {
    const activeId = this.activeConversationId();
    return this.conversations().find((conversation) => conversation.id === activeId)?.messages ?? [];
  });

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
          this.loadConversations(legalCase);
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

  setTotoDraft(message: string): void {
    this.totoDraft.set(message);
  }

  sendTotoMessage(event: Event): void {
    event.preventDefault();
    const message = this.totoDraft().trim();
    if (!message || this.totoLoading()) {
      return;
    }

    this.totoDraft.set('');
    this.totoLoading.set(true);
    this.appendMessage({ role: 'user', text: message });

    this.http
      .post<TotoChatResponse>(this.totoApiUrl, { message, caseId: this.caseId })
      .pipe(finalize(() => this.totoLoading.set(false)))
      .subscribe({
        next: (response) => {
          this.appendMessage({ role: 'assistant', text: response.summary, response });
        },
        error: () => {
          this.appendMessage({
            role: 'assistant',
            text: 'Toto could not reach the case service. Please try again.',
          });
        },
      });
  }

  openConversation(conversationId: string): void {
    this.activeConversationId.set(conversationId);
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
    const activeId = this.activeConversationId();
    this.conversations.update((conversations) =>
      conversations.map((conversation) =>
        conversation.id === activeId
          ? {
              ...conversation,
              subtitle: message.text,
              updatedAt: 'Just now',
              messages: [...conversation.messages, message],
            }
          : conversation,
      ),
    );
    this.persistConversations();
  }

  private loadConversations(legalCase: LegalCaseDetail): void {
    const savedConversations = this.readSavedConversations();
    const conversations = savedConversations.length
      ? savedConversations
      : this.buildSeedConversations(legalCase);

    this.conversations.set(conversations);
    this.activeConversationId.set(conversations[0]?.id ?? '');
    this.persistConversations();
  }

  private readSavedConversations(): ChatConversation[] {
    const rawConversations = window.localStorage.getItem(this.storageKey);
    if (!rawConversations) {
      return [];
    }

    try {
      const conversations = JSON.parse(rawConversations) as ChatConversation[];
      return Array.isArray(conversations) ? conversations : [];
    } catch {
      return [];
    }
  }

  private persistConversations(): void {
    window.localStorage.setItem(this.storageKey, JSON.stringify(this.conversations()));
  }

  private buildSeedConversations(legalCase: LegalCaseDetail): ChatConversation[] {
    const nextDueDate = legalCase.nextDueDate
      ? new Date(legalCase.nextDueDate).toLocaleDateString()
      : 'not currently set';
    const claimAmount = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: 0,
    }).format(legalCase.claimAmount ?? 0);

    return [
      {
        id: 'current-case-brief',
        title: 'Current case brief',
        subtitle: 'Status, owner, and immediate blocker',
        updatedAt: 'Today',
        messages: [
          {
            role: 'assistant',
            text: 'Hi, I’m Toto. Ask me anything about this case — status, correspondence, deadlines, risks, or next actions.',
          },
          {
            role: 'assistant',
            text: `${this.caseTitle(legalCase)} is ${legalCase.status.toLowerCase()}. The next useful checkpoint is ${this.nextActionSummary(legalCase)}`,
          },
        ],
      },
      {
        id: 'correspondence-review',
        title: 'Correspondence review',
        subtitle: 'Latest inbound note and response posture',
        updatedAt: 'Yesterday',
        messages: [
          {
            role: 'user',
            text: 'Summarize the latest correspondence and what we still need before responding.',
          },
          {
            role: 'assistant',
            text: `${legalCase.caseSummary || legalCase.legalIssue || 'No case summary is currently available.'} The response should stay narrow and avoid committing to a position until the record set has been reviewed.`,
          },
        ],
      },
      {
        id: 'deadline-risk-check',
        title: 'Deadline and risk check',
        subtitle: 'Due date, exposure, and priority level',
        updatedAt: 'Apr 24',
        messages: [
          {
            role: 'user',
            text: 'What is the timing risk on this matter?',
          },
          {
            role: 'assistant',
            text: `The next due date is ${nextDueDate} and the priority level is ${legalCase.priority}. The claim amount currently tracked is ${claimAmount}.`,
          },
        ],
      },
    ];
  }

  private get storageKey(): string {
    return `bussiesmw:toto-conversations:${this.caseId}`;
  }

  private get apiOrigin(): string {
    const hostname = window.location.hostname || 'localhost';
    return `http://${hostname}:8000`;
  }
}
