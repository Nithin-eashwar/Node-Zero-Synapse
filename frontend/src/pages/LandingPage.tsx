import { useNavigate } from 'react-router-dom';
import { WebGLShader } from "@/components/ui/web-gl-shader";

export default function LandingPage() {
    const navigate = useNavigate();

    return (
        <div className="relative flex min-h-screen w-full flex-col items-center justify-center overflow-hidden">
            <WebGLShader />
            <div className="relative p-2 w-full mx-auto max-w-3xl">
                <main className="relative py-12 px-4 overflow-visible">
                    <h1
                        className="mb-4 pb-2 text-center text-6xl font-extrabold leading-tight tracking-tighter sm:text-7xl md:text-8xl lg:text-9xl bg-gradient-to-b from-white via-white/90 to-white/40 bg-clip-text text-transparent"
                        style={{ textShadow: '0 0 60px rgba(255,255,255,0.2), 0 0 120px rgba(255,255,255,0.08)' }}
                    >
                        Synapse
                    </h1>
                    <p className="text-white/50 px-6 text-center text-sm md:text-base lg:text-lg tracking-wide">
                        Created by Node Zero
                    </p>
                    <div className="my-8 flex items-center justify-center gap-1.5">
                        <span className="relative flex h-3 w-3 items-center justify-center">
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-500 opacity-75"></span>
                            <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500"></span>
                        </span>
                        <p className="text-xs text-green-500">Available for New Projects</p>
                    </div>

                    <div className="flex justify-center">
                        <button
                            onClick={() => navigate('/dashboard')}
                            className="group relative cursor-pointer inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-8 py-3 text-sm font-semibold text-white backdrop-blur-sm transition-all duration-300 hover:scale-105 hover:border-white/30 hover:bg-white/10 hover:shadow-[0_0_30px_rgba(255,255,255,0.12)] active:scale-95"
                        >
                            <span className="absolute inset-0 rounded-full bg-gradient-to-r from-indigo-500/10 via-cyan-500/10 to-indigo-500/10 opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
                            <span className="relative z-10">Get Started</span>
                            <svg
                                className="relative z-10 h-4 w-4 transition-transform duration-300 group-hover:translate-x-1"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                strokeWidth={2}
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                            </svg>
                        </button>
                    </div>
                </main>
            </div>
        </div>
    );
}
