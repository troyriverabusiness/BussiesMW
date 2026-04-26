import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';

type LegalCaseStatus = 'Open' | 'Closed' | 'Action Required' | 'Awaiting Counterparty' | 'Awaiting Internal';
type CaseFilter = 'All' | LegalCaseStatus;
type RecentFilter = 'all' | 'recent' | 'nonRecent';

interface ServerLegalCase {
  id: string;
  title?: string | null;
  department?: string | null;
  status: LegalCaseStatus;
  priority: 'Low' | 'Medium' | 'High' | 'Critical';
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

interface LegalCase {
  id: string;
  type: string;
  issueSummary: string;
  status: LegalCaseStatus;
  lastUpdated: string;
  recent: boolean;
}

interface TotoMessage {
  role: 'user' | 'assistant';
  text: string;
  caseId?: string;
  status?: TotoMessageStatus;
  activities?: TotoActivity[];
}

interface ChatHistoryMessage {
  role: 'user' | 'assistant';
  content: string;
}

type TotoMessageStatus = 'thinking' | 'using-tools' | 'responding' | 'complete' | 'error';

interface TotoActivity {
  name: string;
  args?: Record<string, unknown>;
  status: 'running' | 'completed';
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

@Component({
  selector: 'app-dashboard',
  imports: [CommonModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class DashboardComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly apiUrl = `${this.apiOrigin}/api/v1/cases`;
  private readonly chatApiUrl = `${this.apiOrigin}/api/v1/chat`;

  readonly cases = signal<LegalCase[]>([]);
  readonly activeFilter = signal<CaseFilter>('Action Required');
  readonly activeRecentFilter = signal<RecentFilter>('all');
  readonly filtersOpen = signal(false);
  readonly searchQuery = signal('');
  readonly pageIndex = signal(0);
  readonly isLoading = signal(true);
  readonly errorMessage = signal('');
  readonly totoOpen = signal(false);
  readonly totoLoading = signal(false);
  readonly totoMuted = signal(false);
  readonly totoDraft = signal('');
  readonly totoMessages = signal<TotoMessage[]>([]);
  readonly filters: CaseFilter[] = [
    'Action Required',
    'All',
    'Open',
    'Awaiting Counterparty',
    'Awaiting Internal',
    'Closed',
  ];
  readonly recentFilters: Array<{ label: string; value: RecentFilter }> = [
    { label: 'All cases', value: 'all' },
    { label: 'Recent only', value: 'recent' },
    { label: 'Non-recent only', value: 'nonRecent' },
  ];
  readonly pageSize = 10;

  readonly filteredCases = computed(() => {
    const filter = this.activeFilter();
    const recentFilter = this.activeRecentFilter();
    const query = this.searchQuery().trim().toLowerCase();
    const filtered = this.cases().filter((legalCase) => {
      const matchesFilter = filter === 'All' || legalCase.status === filter;
      const matchesRecentFilter =
        recentFilter === 'all' ||
        (recentFilter === 'recent' && legalCase.recent) ||
        (recentFilter === 'nonRecent' && !legalCase.recent);
      const searchableText = [
        legalCase.id,
        legalCase.type,
        legalCase.issueSummary,
        legalCase.status,
      ]
        .join(' ')
        .toLowerCase();

      return matchesFilter && matchesRecentFilter && (!query || searchableText.includes(query));
    });

    return [...filtered].sort((firstCase, secondCase) => {
      const firstDate = new Date(firstCase.lastUpdated).getTime();
      const secondDate = new Date(secondCase.lastUpdated).getTime();
      return secondDate - firstDate;
    });
  });

  readonly totalPages = computed(() => Math.max(1, Math.ceil(this.filteredCases().length / this.pageSize)));
  readonly paginatedCases = computed(() => {
    const start = this.pageIndex() * this.pageSize;
    return this.filteredCases().slice(start, start + this.pageSize);
  });

  ngOnInit(): void {
    this.http
      .get<ServerLegalCase[]>(this.apiUrl)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: (cases) => {
          this.cases.set(cases.map((legalCase) => this.toDashboardCase(legalCase)));
        },
        error: () => {
          this.errorMessage.set('Case data is unavailable. Verify that the FastAPI service is running.');
        },
      });
  }

  setFilter(filter: CaseFilter): void {
    this.activeFilter.set(filter);
    this.pageIndex.set(0);
  }

  setRecentFilter(filter: RecentFilter): void {
    this.activeRecentFilter.set(filter);
    this.pageIndex.set(0);
  }

  toggleFilters(): void {
    this.filtersOpen.update((isOpen) => !isOpen);
  }

  toggleToto(): void {
    this.totoOpen.update((isOpen) => !isOpen);
    this.playTone(520, 0.035);
  }

  toggleTotoMute(): void {
    this.totoMuted.update((isMuted) => !isMuted);
  }

  setSearchQuery(query: string): void {
    this.searchQuery.set(query);
    this.pageIndex.set(0);
  }

  setTotoDraft(message: string): void {
    this.totoDraft.set(message);
  }

  sendTotoDraft(event: Event): void {
    event.preventDefault();
    const request = this.totoDraft().trim();
    if (!request || this.totoLoading()) {
      return;
    }

    this.totoDraft.set('');
    this.sendTotoRequest(request);
  }

  requestCaseUpdate(legalCase: LegalCase, event: Event): void {
    event.stopPropagation();
    this.totoOpen.set(true);
    this.sendTotoRequest('Give me an update on this case.', legalCase.id);
  }

  nextPage(): void {
    this.pageIndex.update((index) => Math.min(index + 1, this.totalPages() - 1));
  }

  previousPage(): void {
    this.pageIndex.update((index) => Math.max(index - 1, 0));
  }

  openCase(legalCase: LegalCase): void {
    void this.router.navigate(['/cases', legalCase.id]);
  }

  private async sendTotoRequest(request: string, caseId?: string): Promise<void> {
    this.totoLoading.set(true);
    const history = this.toChatHistory();
    this.totoMessages.update((messages) => [...messages, { role: 'user', text: request, caseId }]);
    this.totoMessages.update((messages) => [
      ...messages,
      { role: 'assistant', text: '', status: 'thinking', activities: [] },
    ]);
    this.playTone(440, 0.025);

    try {
      await this.streamChatResponse({ message: request, caseId, messages: history });
      this.ensureAssistantMessageText('Toto did not return a response.');
      this.setLastAssistantStatus('complete');
      this.playTone(660, 0.04);
    } catch {
      this.replaceLastAssistantMessage('Toto could not reach the AI chat service. Please try again.');
      this.setLastAssistantStatus('error');
    } finally {
      this.totoLoading.set(false);
    }
  }

  assistantStatusLabel(message: TotoMessage): string {
    if (message.role !== 'assistant') {
      return '';
    }

    if (message.status === 'using-tools') {
      return 'Using case tools';
    }
    if (message.status === 'responding') {
      return 'Streaming response';
    }
    if (message.status === 'error') {
      return 'Response interrupted';
    }
    if (message.status === 'thinking') {
      return 'Reviewing context';
    }
    return message.activities?.length ? 'Context checked' : '';
  }

  assistantStatusIcon(message: TotoMessage): string {
    if (message.status === 'complete') {
      return 'check_circle';
    }
    if (message.status === 'error') {
      return 'error';
    }
    return 'progress_activity';
  }

  isAssistantStatusLive(message: TotoMessage): boolean {
    return (
      message.status === 'thinking' ||
      message.status === 'using-tools' ||
      message.status === 'responding'
    );
  }

  shouldShowThinking(message: TotoMessage): boolean {
    return (
      message.status === 'thinking' ||
      message.status === 'using-tools' ||
      message.status === 'responding' ||
      message.status === 'error'
    );
  }

  thinkingStatusLabel(message: TotoMessage): string {
    if (message.status === 'responding') {
      return 'Writing response';
    }
    if (message.status === 'error') {
      return 'Response interrupted';
    }
    return 'Thinking';
  }

  toolCallStatusLabel(activity: TotoActivity): string {
    const action = activity.status === 'completed' ? 'Called tool' : 'Calling tool';
    return `${action}: ${this.activityLabel(activity)}`;
  }

  activityLabel(activity: TotoActivity): string {
    const labels: Record<string, string> = {
      list_cases: 'List cases',
      get_case: 'Case lookup',
      list_case_traces: 'Trace lookup',
      contact_internal_employee: 'Contact internal employee',
    };
    return labels[activity.name] ?? this.toTitleCase(activity.name.replace(/^get_/, '').replace(/_/g, ' '));
  }

  activityIcon(activity: TotoActivity): string {
    const icons: Record<string, string> = {
      list_cases: 'folder_open',
      get_case: 'clinical_notes',
      list_case_traces: 'timeline',
      contact_internal_employee: 'mail',
    };
    return icons[activity.name] ?? 'construction';
  }

  renderMessageText(text: string): string {
    return this.markdownToHtml(text);
  }

  private async streamChatResponse(payload: {
    message: string;
    caseId?: string;
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

    const event = JSON.parse(rawData) as ChatStreamEvent;
    if (event.error) {
      throw new Error(event.error);
    }
    if (event.tool_call) {
      this.recordToolCall(event.tool_call);
    }
    if (event.tool_result) {
      this.completeToolCall(event.tool_result.name);
    }
    if (event.content) {
      this.setLastAssistantStatus('responding');
      this.appendToLastAssistantMessage(event.content);
    }
  }

  private appendToLastAssistantMessage(content: string): void {
    this.totoMessages.update((messages) => {
      const nextMessages = [...messages];
      const lastMessage = nextMessages.at(-1);
      if (lastMessage?.role === 'assistant') {
        nextMessages[nextMessages.length - 1] = {
          ...lastMessage,
          text: `${lastMessage.text}${content}`,
        };
      }
      return nextMessages;
    });
  }

  private replaceLastAssistantMessage(text: string): void {
    this.totoMessages.update((messages) => {
      const nextMessages = [...messages];
      const lastMessage = nextMessages.at(-1);
      if (lastMessage?.role === 'assistant') {
        nextMessages[nextMessages.length - 1] = { ...lastMessage, text };
      }
      return nextMessages;
    });
  }

  private recordToolCall(toolCall: { name: string; args: Record<string, unknown> }): void {
    this.totoMessages.update((messages) => {
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

  private completeToolCall(toolName: string): void {
    this.totoMessages.update((messages) => {
      const nextMessages = [...messages];
      const lastMessage = nextMessages.at(-1);
      if (lastMessage?.role === 'assistant') {
        nextMessages[nextMessages.length - 1] = {
          ...lastMessage,
          status: lastMessage.text.trim() ? 'responding' : 'using-tools',
          activities: (lastMessage.activities ?? []).map((activity) =>
            activity.name === toolName ? { ...activity, status: 'completed' } : activity,
          ),
        };
      }
      return nextMessages;
    });
  }

  private setLastAssistantStatus(status: TotoMessageStatus): void {
    this.totoMessages.update((messages) => {
      const nextMessages = [...messages];
      const lastMessage = nextMessages.at(-1);
      if (lastMessage?.role === 'assistant') {
        nextMessages[nextMessages.length - 1] = { ...lastMessage, status };
      }
      return nextMessages;
    });
  }

  private ensureAssistantMessageText(fallback: string): void {
    const lastMessage = this.totoMessages().at(-1);
    if (lastMessage?.role === 'assistant' && !lastMessage.text.trim()) {
      this.replaceLastAssistantMessage(fallback);
    }
  }

  private toChatHistory(): ChatHistoryMessage[] {
    return this.totoMessages()
      .filter((message) => message.text.trim())
      .map((message) => ({ role: message.role, content: message.text }));
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

  private playTone(frequency: number, duration: number): void {
    if (this.totoMuted()) {
      return;
    }

    const AudioContextClass =
      window.AudioContext ||
      (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextClass) {
      return;
    }

    const audioContext = new AudioContextClass();
    const oscillator = audioContext.createOscillator();
    const gain = audioContext.createGain();

    oscillator.frequency.value = frequency;
    oscillator.type = 'sine';
    gain.gain.value = 0.018;
    oscillator.connect(gain);
    gain.connect(audioContext.destination);
    oscillator.start();
    oscillator.stop(audioContext.currentTime + duration);
    oscillator.onended = () => audioContext.close();
  }

  filterCount(filter: CaseFilter): number {
    if (filter === 'All') {
      return this.cases().length;
    }

    return this.cases().filter((legalCase) => legalCase.status === filter).length;
  }

  recentFilterCount(filter: RecentFilter): number {
    if (filter === 'all') {
      return this.cases().length;
    }

    return this.cases().filter((legalCase) => (filter === 'recent' ? legalCase.recent : !legalCase.recent)).length;
  }

  statusClass(status: LegalCaseStatus): string {
    return status.toLowerCase().replace(/\s+/g, '-');
  }

  trackCase(_: number, legalCase: LegalCase): string {
    return legalCase.id;
  }

  private toDashboardCase(legalCase: ServerLegalCase): LegalCase {
    return {
      id: legalCase.id,
      type: legalCase.department || legalCase.title || 'Legal case',
      issueSummary:
        legalCase.legalIssue ||
        legalCase.caseSummary ||
        legalCase.title ||
        this.partiesSummary(legalCase) ||
        'No issue summary available',
      status: legalCase.status,
      lastUpdated: legalCase.lastUpdateDate,
      recent: this.isRecent(legalCase.lastUpdateDate),
    };
  }

  private isRecent(value: string): boolean {
    const timestamp = new Date(value).getTime();
    if (Number.isNaN(timestamp)) {
      return false;
    }

    const sevenDaysInMilliseconds = 7 * 24 * 60 * 60 * 1000;
    return Date.now() - timestamp <= sevenDaysInMilliseconds;
  }

  private partiesSummary(legalCase: ServerLegalCase): string {
    return [legalCase.plaintiff, legalCase.defendant].filter(Boolean).join(' vs ');
  }

  private get apiOrigin(): string {
    const hostname = window.location.hostname || 'localhost';
    return `http://${hostname}:8000`;
  }
}
