import { useState } from 'react';
import { UploadCard } from './components/UploadCard';
import { ATSScoreCard } from './components/ATSScoreCard';
import { SkillBreakdown } from './components/SkillBreakdown';
import { Suggestions } from './components/Suggestions';
import { ResumePreview } from './components/ResumePreview';
import { EmptyState } from './components/EmptyState';
import { ErrorState } from './components/ErrorState';
import { Sparkles, FileText } from 'lucide-react';

export default function App() {
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [error, setError] = useState(false);

  const handleAnalyze = async () => {
    if (!resumeFile || !jobDescription.trim()) return;

    setIsAnalyzing(true);
    setError(false);

    // Simulate analysis
    setTimeout(() => {
      setIsAnalyzing(false);
      setShowResults(true);
    }, 2000);
  };

  const handleReset = () => {
    setShowResults(false);
    setError(false);
  };

  // Mock data for demonstration
  const mockResults = {
    score: 78,
    improvement: 15,
    confidence: 92,
    technicalSkills: [
      { name: 'React', status: 'matched' as const },
      { name: 'TypeScript', status: 'matched' as const },
      { name: 'Node.js', status: 'partial' as const },
      { name: 'GraphQL', status: 'missing' as const },
      { name: 'AWS', status: 'matched' as const },
      { name: 'Docker', status: 'partial' as const },
    ],
    softSkills: [
      { name: 'Leadership', status: 'matched' as const },
      { name: 'Communication', status: 'matched' as const },
      { name: 'Problem Solving', status: 'partial' as const },
      { name: 'Agile', status: 'missing' as const },
    ],
    suggestions: [
      'Add quantifiable metrics to your achievements (e.g., "Increased performance by 40%")',
      'Include GraphQL experience or remove from job requirements if not critical',
      'Emphasize leadership and team collaboration in project descriptions',
      'Add specific AWS services you\'ve worked with (Lambda, EC2, S3)',
      'Include keywords like "scalable" and "microservices" from the job description',
    ],
    resumeSections: [
      {
        title: 'Professional Summary',
        content: [
          'Senior Full-Stack Developer with 5+ years of experience building scalable web applications using React, TypeScript, and Node.js. Proven track record of leading cross-functional teams and delivering high-impact solutions in fast-paced environments.',
        ],
      },
      {
        title: 'Technical Skills',
        content: [
          'Frontend: React, TypeScript, Next.js, Tailwind CSS',
          'Backend: Node.js, Express, REST APIs, Microservices',
          'Cloud & DevOps: AWS (Lambda, EC2, S3), Docker, CI/CD',
          'Tools: Git, Agile/Scrum, Jest, Webpack',
        ],
      },
      {
        title: 'Professional Experience',
        content: [
          'Led team of 6 developers to deliver scalable e-commerce platform, increasing conversion rate by 32%',
          'Architected and implemented microservices architecture reducing API response time by 45%',
          'Mentored junior developers and established code review best practices',
        ],
      },
    ],
  };

  const canAnalyze = resumeFile && jobDescription.trim().length > 0;

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="mb-12">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-6 h-6 text-primary" />
            <h1 className="text-foreground">Resume Analyzer</h1>
          </div>
          <p className="text-muted-foreground">
            AI-powered ATS optimization to help you land your next role
          </p>
        </div>

        {/* Input Section */}
        {!showResults && (
          <div className="grid lg:grid-cols-2 gap-6 mb-8">
            {/* Left: Resume Upload */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-muted-foreground" />
                <label className="text-foreground">Your Resume</label>
              </div>
              <UploadCard onFileUpload={setResumeFile} />
            </div>

            {/* Right: Job Description */}
            <div className="space-y-4">
              <label className="text-foreground">Job Description</label>
              <textarea
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste the job description here..."
                className="w-full h-[200px] px-4 py-3 bg-input-background border border-border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-ring transition-shadow text-foreground placeholder:text-muted-foreground"
              />
            </div>
          </div>
        )}

        {/* Analyze Button */}
        {!showResults && (
          <div className="flex justify-center">
            <button
              onClick={handleAnalyze}
              disabled={!canAnalyze || isAnalyzing}
              className={`
                px-8 py-3 rounded-lg transition-all
                ${canAnalyze && !isAnalyzing
                  ? 'bg-primary text-primary-foreground hover:opacity-90 shadow-sm'
                  : 'bg-muted text-muted-foreground cursor-not-allowed'
                }
              `}
            >
              {isAnalyzing ? (
                <span className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                  Analyzing...
                </span>
              ) : (
                'Analyze Resume'
              )}
            </button>
          </div>
        )}

        {/* Empty State */}
        {!showResults && !isAnalyzing && (
          <EmptyState />
        )}

        {/* Error State */}
        {error && (
          <ErrorState onRetry={handleReset} />
        )}

        {/* Results Section */}
        {showResults && !error && (
          <div className="space-y-6">
            {/* Back Button */}
            <button
              onClick={handleReset}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              ← Analyze another resume
            </button>

            {/* ATS Score */}
            <ATSScoreCard
              score={mockResults.score}
              improvement={mockResults.improvement}
              confidence={mockResults.confidence}
            />

            {/* Two Column Layout for Skills and Suggestions */}
            <div className="grid lg:grid-cols-2 gap-6">
              <SkillBreakdown
                technicalSkills={mockResults.technicalSkills}
                softSkills={mockResults.softSkills}
              />
              <Suggestions suggestions={mockResults.suggestions} />
            </div>

            {/* Resume Preview */}
            <ResumePreview sections={mockResults.resumeSections} />
          </div>
        )}
      </div>
    </div>
  );
}