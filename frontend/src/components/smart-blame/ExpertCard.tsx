import { motion } from 'framer-motion';
import { Quote, Star } from 'lucide-react';
import type { ExpertProfile } from '../../types';

interface ExpertCardProps {
    expert: ExpertProfile;
}

/** SVG Circular Progress Ring */
function ScoreRing({ score }: { score: number }) {
    const radius = 54;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference * (1 - score);

    return (
        <div className="relative flex h-36 w-36 items-center justify-center">
            <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120">
                {/* Track */}
                <circle
                    cx="60"
                    cy="60"
                    r={radius}
                    fill="none"
                    stroke="rgba(255,255,255,0.06)"
                    strokeWidth="4"
                />
                {/* Progress */}
                <motion.circle
                    cx="60"
                    cy="60"
                    r={radius}
                    fill="none"
                    stroke="url(#scoreGrad)"
                    strokeWidth="4"
                    strokeLinecap="round"
                    strokeDasharray={circumference}
                    initial={{ strokeDashoffset: circumference }}
                    animate={{ strokeDashoffset: offset }}
                    transition={{ duration: 1.2, ease: 'easeOut' }}
                />
                <defs>
                    <linearGradient id="scoreGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#818cf8" />
                        <stop offset="100%" stopColor="#22d3ee" />
                    </linearGradient>
                </defs>
            </svg>
            {/* Center text */}
            <div className="absolute flex flex-col items-center">
                <span className="text-3xl font-semibold tabular-nums text-white">{Math.round(score * 100)}</span>
                <span className="text-[10px] text-neutral-600">Score</span>
            </div>
        </div>
    );
}

export default function ExpertCard({ expert }: ExpertCardProps) {
    return (
        <div className="rounded-2xl border border-indigo-500/10 bg-indigo-500/[0.03] p-6">
            {/* Top section: Avatar + Score Ring */}
            <div className="flex items-center gap-6">
                {/* Avatar */}
                <div className="flex flex-col items-center gap-2">
                    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-cyan-400 text-2xl font-semibold text-white">
                        {expert.name.split(' ').map((w) => w[0]).join('')}
                    </div>
                    <div className="text-center">
                        <p className="text-sm font-medium text-white">{expert.name}</p>
                        <p className="text-[10px] text-neutral-600">{expert.email}</p>
                    </div>
                </div>

                {/* Score Ring */}
                <ScoreRing score={expert.totalScore} />

                {/* Confidence & Recommendation */}
                <div className="flex-1 space-y-3">
                    <div className="flex items-center gap-2">
                        <Star className="h-4 w-4 text-amber-400" />
                        <span className="text-xs text-neutral-500">
                            Confidence: <span className="font-medium text-white">{Math.round(expert.confidence * 100)}%</span>
                        </span>
                    </div>
                    <div className="flex items-start gap-2 rounded-xl bg-indigo-500/[0.06] p-3">
                        <Quote className="mt-0.5 h-4 w-4 shrink-0 text-indigo-400" />
                        <p className="text-sm font-medium italic text-indigo-300/80">
                            "{expert.recommendation}"
                        </p>
                    </div>
                </div>
            </div>

            {/* Expertise Factors */}
            <div className="mt-6">
                <h4 className="mb-3 text-xs font-medium text-neutral-500">Expertise Breakdown</h4>
                <div className="space-y-2.5">
                    {expert.factors.map((f, i) => (
                        <motion.div
                            key={f.name}
                            initial={{ opacity: 0, x: -16 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.3 + i * 0.06 }}
                            className="flex items-center gap-3"
                        >
                            <span className="w-28 shrink-0 text-right text-[11px] text-neutral-500">
                                {f.label}
                            </span>
                            <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-white/[0.04]">
                                <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${f.value * 100}%` }}
                                    transition={{ duration: 0.8, delay: 0.4 + i * 0.06 }}
                                    className="absolute inset-y-0 left-0 rounded-full"
                                    style={{ backgroundColor: f.color }}
                                />
                            </div>
                            <span className="w-10 text-right text-[11px] font-medium tabular-nums text-neutral-400">
                                {Math.round(f.value * 100)}%
                            </span>
                        </motion.div>
                    ))}
                </div>
            </div>
        </div>
    );
}
