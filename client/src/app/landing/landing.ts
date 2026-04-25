import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

interface FeatureCard {
  title: string;
  description: string;
  points: string[];
}

@Component({
  selector: 'app-landing',
  imports: [CommonModule, RouterLink],
  templateUrl: './landing.html',
  styleUrl: './landing.scss',
})
export class LandingComponent {
  readonly valuePoints = [
    'Move matters from intake to action faster',
    'Reduce manual legal operations work',
    'Expose status, risk, and ownership clearly',
    'Keep compliance and auditability in the workflow',
  ];

  readonly features: FeatureCard[] = [
    {
      title: 'Intelligent Case Intake',
      description: 'Classify requests and route them to the right workflow.',
      points: [
        'Detect issue type: litigation, compliance, contracts',
        'Route to the correct workflow instantly',
        'Reduce manual triage work',
      ],
    },
    {
      title: 'Multi-Agent Legal Execution',
      description: 'Specialized agents collaborate across legal workstreams.',
      points: [
        'Contract Agent',
        'Compliance Agent',
        'Research Agent',
        'Risk Agent',
        'Orchestrator Agent',
      ],
    },
    {
      title: 'Workflow Orchestration Engine',
      description: 'Tasks are coordinated, not just processed.',
      points: ['Delegate tasks between agents', 'Manage dependencies', 'Merge results into one output'],
    },
    {
      title: 'Compliance & Risk Intelligence',
      description: 'Risk checks remain visible and reviewable.',
      points: ['Sanctions & ESG checks', 'Jurisdiction-aware analysis', 'Risk scoring for every case'],
    },
    {
      title: 'Structured Legal Outputs',
      description: 'Clear outputs lawyers can review quickly.',
      points: ['Clean summaries', 'Action recommendations', 'Audit-ready documentation'],
    },
    {
      title: 'Transparency & Traceability',
      description: 'Every step has context and a record.',
      points: ['Full activity logs', 'Decision paths', 'Audit trails'],
    },
    {
      title: 'Human-in-the-Loop Control',
      description: 'Lawyers approve, intervene, and override.',
      points: ['Review and approve outputs', 'Intervene at any stage', 'Override decisions'],
    },
  ];

  readonly useCases = [
    'Contract drafting and review',
    'Litigation case processing',
    'Internal legal inquiries',
    'Compliance monitoring',
    'Knowledge retrieval',
  ];

  readonly benefits = [
    'Reduce manual workload',
    'Faster case turnaround',
    'Lower legal risk exposure',
    'Standardized decision-making',
    'Scalable legal operations',
  ];

  readonly trustPoints = [
    'Data privacy-first architecture',
    'Modular and scalable',
    'Built for integration with enterprise systems',
    'Audit-ready by design',
  ];
}
