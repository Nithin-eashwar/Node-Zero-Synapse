import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, Github, ArrowRight, FileArchive, X, Sparkles, LogOut } from 'lucide-react';
import { WebGLShader } from '@/components/ui/web-gl-shader';
import { API_BASE } from '@/lib/api';
import { useUploadFolder, useUploadGithub } from '@/lib/hooks';
import { useAuth } from '@/lib/AuthContext';

export default function LandingPage() {
    const navigate = useNavigate();
    const { user, loading, signInWithGoogle, signInWithGithub, signOut } = useAuth();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [githubUrl, setGithubUrl] = useState('');
    const [dragOver, setDragOver] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [authError, setAuthError] = useState<string | null>(null);

    const uploadFolder = useUploadFolder();
    const uploadGithub = useUploadGithub();

    const handleFileSelect = useCallback((file: File) => {
        if (!file.name.endsWith('.zip')) {
            setError('Please select a .zip file');
            return;
        }
        setError(null);
        setSelectedFile(file);
    }, []);

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            setDragOver(false);
            const file = e.dataTransfer.files[0];
            if (file) handleFileSelect(file);
        },
        [handleFileSelect]
    );

    const handleUploadFolder = async () => {
        if (!selectedFile) return;
        setError(null);
        try {
            const formData = new FormData();
            formData.append('file', selectedFile);
            const res = await fetch(`${API_BASE}/upload/folder`, {
                method: 'POST',
                body: formData,
            });
            if (!res.ok) throw new Error('Upload failed');
            navigate('/analyzing');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Upload failed. Is the backend running?');
        }
    };

    const handleUploadGithub = async () => {
        const url = githubUrl.trim();
        if (!url) return;
        if (!url.startsWith('https://github.com/')) {
            setError('Please enter a valid GitHub URL (https://github.com/...)');
            return;
        }
        setError(null);
        try {
            const res = await fetch(`${API_BASE}/upload/github`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url }),
            });
            if (!res.ok) throw new Error('Clone failed');
            navigate('/analyzing');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Clone failed. Is the backend running?');
        }
    };

    const handleGoogleSignIn = async () => {
        setAuthError(null);
        try {
            await signInWithGoogle();
        } catch (err) {
            setAuthError(err instanceof Error ? err.message : 'Sign-in failed');
        }
    };

    const handleGithubSignIn = async () => {
        setAuthError(null);
        try {
            await signInWithGithub();
        } catch (err) {
            setAuthError(err instanceof Error ? err.message : 'Sign-in failed');
        }
    };

    const isLoading = uploadFolder.isPending || uploadGithub.isPending;

    return (
        <div className="relative flex min-h-screen w-full flex-col items-center justify-center overflow-hidden">
            <WebGLShader />
            <div className="relative z-10 w-full max-w-2xl px-4">
                <main className="relative py-12 px-4 overflow-visible">
                    {/* Title */}
                    <motion.h1
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6 }}
                        className="mb-4 pb-2 text-center text-6xl font-extrabold leading-tight tracking-tighter sm:text-7xl md:text-8xl lg:text-9xl bg-gradient-to-b from-white via-white/90 to-white/40 bg-clip-text text-transparent"
                        style={{ textShadow: '0 0 60px rgba(255,255,255,0.2), 0 0 120px rgba(255,255,255,0.08)' }}
                    >
                        Synapse
                    </motion.h1>

                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.2, duration: 0.5 }}
                        className="text-white/50 px-6 text-center text-sm md:text-base lg:text-lg tracking-wide"
                    >
                        {user
                            ? 'Upload your codebase to unlock GraphRAG-powered intelligence'
                            : 'Sign in to get started with codebase intelligence'}
                    </motion.p>

                    {/* Status indicator */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.3 }}
                        className="my-6 flex items-center justify-center gap-1.5"
                    >
                        <span className="relative flex h-3 w-3 items-center justify-center">
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-500 opacity-75" />
                            <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
                        </span>
                        <p className="text-xs text-green-500">
                            {user ? `Signed in as ${user.displayName || user.email}` : 'Ready'}
                        </p>
                    </motion.div>

                    <AnimatePresence mode="wait">
                        {/* ─── AUTH SCREEN ─── */}
                        {!user && !loading && (
                            <motion.div
                                key="auth"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                transition={{ delay: 0.4, duration: 0.5 }}
                                className="rounded-2xl border border-white/[0.08] bg-black/40 p-6 backdrop-blur-xl"
                            >
                                <div className="space-y-3">
                                    {/* Google Sign-In */}
                                    <button
                                        onClick={handleGoogleSignIn}
                                        className="group w-full flex items-center justify-center gap-3 rounded-xl border border-white/10 bg-white px-4 py-3 text-sm font-semibold text-gray-800 transition-all duration-300 hover:shadow-[0_0_30px_rgba(255,255,255,0.1)] hover:scale-[1.02] active:scale-[0.98]"
                                    >
                                        <svg className="h-5 w-5" viewBox="0 0 24 24">
                                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
                                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                                        </svg>
                                        Continue with Google
                                    </button>

                                    {/* GitHub Sign-In */}
                                    <button
                                        onClick={handleGithubSignIn}
                                        className="group w-full flex items-center justify-center gap-3 rounded-xl border border-white/10 bg-[#161b22] px-4 py-3 text-sm font-semibold text-white transition-all duration-300 hover:bg-[#1f2937] hover:shadow-[0_0_30px_rgba(255,255,255,0.06)] hover:scale-[1.02] active:scale-[0.98]"
                                    >
                                        <Github className="h-5 w-5" />
                                        Continue with GitHub
                                    </button>
                                </div>

                                {/* Auth Error */}
                                <AnimatePresence>
                                    {authError && (
                                        <motion.div
                                            initial={{ opacity: 0, height: 0 }}
                                            animate={{ opacity: 1, height: 'auto' }}
                                            exit={{ opacity: 0, height: 0 }}
                                            className="mt-4 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-2 text-sm text-red-300"
                                        >
                                            {authError}
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </motion.div>
                        )}

                        {/* ─── LOADING AUTH STATE ─── */}
                        {loading && (
                            <motion.div
                                key="loading"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                className="flex justify-center py-8"
                            >
                                <div className="h-6 w-6 animate-spin rounded-full border-2 border-white/20 border-t-white/60" />
                            </motion.div>
                        )}

                        {/* ─── UPLOAD PANEL (after auth) ─── */}
                        {user && (
                            <motion.div
                                key="upload"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                transition={{ duration: 0.5 }}
                                className="rounded-2xl border border-white/[0.08] bg-black/40 p-6 backdrop-blur-xl"
                            >
                                {/* User bar */}
                                <div className="mb-4 flex items-center justify-between rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2">
                                    <div className="flex items-center gap-2">
                                        {user.photoURL && (
                                            <img src={user.photoURL} alt="" className="h-6 w-6 rounded-full" />
                                        )}
                                        <span className="text-xs text-white/50 truncate max-w-[200px]">
                                            {user.displayName || user.email}
                                        </span>
                                    </div>
                                    <button
                                        onClick={signOut}
                                        className="flex items-center gap-1 text-[11px] text-white/30 transition-colors hover:text-white/60"
                                    >
                                        <LogOut className="h-3 w-3" />
                                        Sign out
                                    </button>
                                </div>

                                {/* Upload options */}
                                <div className="grid gap-4 md:grid-cols-2">
                                    {/* Upload ZIP */}
                                    <div className="space-y-3">
                                        <div className="flex items-center gap-2 text-sm font-medium text-white/70">
                                            <Upload className="h-4 w-4 text-indigo-400" />
                                            Upload Folder (ZIP)
                                        </div>

                                        <div
                                            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                                            onDragLeave={() => setDragOver(false)}
                                            onDrop={handleDrop}
                                            onClick={() => fileInputRef.current?.click()}
                                            className={`group cursor-pointer rounded-xl border-2 border-dashed p-6 text-center transition-all duration-300 ${dragOver
                                                ? 'border-indigo-500/60 bg-indigo-500/10'
                                                : selectedFile
                                                    ? 'border-green-500/30 bg-green-500/5'
                                                    : 'border-white/[0.08] bg-white/[0.02] hover:border-white/[0.15] hover:bg-white/[0.04]'
                                                }`}
                                        >
                                            <input
                                                ref={fileInputRef}
                                                type="file"
                                                accept=".zip"
                                                className="hidden"
                                                onChange={(e) => {
                                                    const file = e.target.files?.[0];
                                                    if (file) handleFileSelect(file);
                                                }}
                                            />
                                            <AnimatePresence mode="wait">
                                                {selectedFile ? (
                                                    <motion.div
                                                        key="selected"
                                                        initial={{ opacity: 0, scale: 0.9 }}
                                                        animate={{ opacity: 1, scale: 1 }}
                                                        exit={{ opacity: 0, scale: 0.9 }}
                                                        className="flex flex-col items-center gap-2"
                                                    >
                                                        <FileArchive className="h-8 w-8 text-green-400" />
                                                        <span className="text-sm font-medium text-green-300 truncate max-w-full">
                                                            {selectedFile.name}
                                                        </span>
                                                        <span className="text-[11px] text-white/30">
                                                            {(selectedFile.size / 1024 / 1024).toFixed(1)} MB
                                                        </span>
                                                        <button
                                                            onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}
                                                            className="mt-1 flex items-center gap-1 text-[11px] text-white/40 hover:text-white/60 transition-colors"
                                                        >
                                                            <X className="h-3 w-3" /> Remove
                                                        </button>
                                                    </motion.div>
                                                ) : (
                                                    <motion.div
                                                        key="empty"
                                                        initial={{ opacity: 0 }}
                                                        animate={{ opacity: 1 }}
                                                        exit={{ opacity: 0 }}
                                                        className="flex flex-col items-center gap-2"
                                                    >
                                                        <Upload className="h-8 w-8 text-white/20 transition-colors group-hover:text-white/40" />
                                                        <span className="text-sm text-white/30 group-hover:text-white/50 transition-colors">
                                                            Drop ZIP or click to browse
                                                        </span>
                                                    </motion.div>
                                                )}
                                            </AnimatePresence>
                                        </div>

                                        <button
                                            onClick={handleUploadFolder}
                                            disabled={!selectedFile || isLoading}
                                            className="w-full group relative inline-flex items-center justify-center gap-2 rounded-xl border border-white/15 bg-indigo-600/20 px-4 py-2.5 text-sm font-semibold text-white backdrop-blur-sm transition-all duration-300 hover:bg-indigo-600/30 hover:border-indigo-500/40 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-indigo-600/20"
                                        >
                                            <Sparkles className="h-4 w-4" />
                                            {uploadFolder.isPending ? 'Uploading...' : 'Analyze Codebase'}
                                        </button>
                                    </div>

                                    {/* Divider */}
                                    <div className="hidden md:flex items-center justify-center relative">
                                        <div className="absolute inset-y-0 left-0 w-px bg-gradient-to-b from-transparent via-white/[0.08] to-transparent" />
                                    </div>

                                    {/* GitHub URL */}
                                    <div className="space-y-3 md:col-start-2 md:row-start-1">
                                        <div className="flex items-center gap-2 text-sm font-medium text-white/70">
                                            <Github className="h-4 w-4 text-white/70" />
                                            GitHub Repository
                                        </div>

                                        <div className="space-y-3">
                                            <input
                                                type="url"
                                                value={githubUrl}
                                                onChange={(e) => { setGithubUrl(e.target.value); setError(null); }}
                                                onKeyDown={(e) => { if (e.key === 'Enter') handleUploadGithub(); }}
                                                placeholder="https://github.com/user/repo"
                                                className="w-full rounded-xl border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-sm text-white placeholder-white/20 outline-none transition-all duration-300 focus:border-white/[0.2] focus:bg-white/[0.05] focus:ring-1 focus:ring-white/10"
                                            />

                                            <button
                                                onClick={handleUploadGithub}
                                                disabled={!githubUrl.trim() || isLoading}
                                                className="w-full group relative inline-flex items-center justify-center gap-2 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm font-semibold text-white backdrop-blur-sm transition-all duration-300 hover:bg-white/10 hover:border-white/25 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-white/5"
                                            >
                                                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                                                {uploadGithub.isPending ? 'Cloning...' : 'Clone & Analyze'}
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                {/* Error */}
                                <AnimatePresence>
                                    {error && (
                                        <motion.div
                                            initial={{ opacity: 0, height: 0 }}
                                            animate={{ opacity: 1, height: 'auto' }}
                                            exit={{ opacity: 0, height: 0 }}
                                            className="mt-4 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-2 text-sm text-red-300"
                                        >
                                            {error}
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Subtitle */}
                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.6 }}
                        className="mt-4 text-center text-[11px] text-white/20"
                    >
                        Supports Python codebases · Blast Radius · Smart Blame · Governance
                    </motion.p>
                </main>
            </div>
        </div>
    );
}
