import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

export interface LegalDataHubSource {
  title: string;
  court?: string;
  date?: string;
  ecli?: string;
  aktenzeichen?: string;
  document_type?: string;
  relevance_score?: number;
  excerpt?: string;
  why_used?: string;
}

@Component({
  selector: 'app-legal-source-list',
  imports: [CommonModule],
  templateUrl: './legal-source-list.component.html',
  styleUrl: './legal-source-list.component.scss',
})
export class LegalSourceListComponent {
  @Input() sources: LegalDataHubSource[] = [];

  relevanceLabel(source: LegalDataHubSource): string {
    return typeof source.relevance_score === 'number' ? source.relevance_score.toFixed(2) : 'Not scored';
  }
}
