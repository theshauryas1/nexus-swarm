import React, { useEffect, useState } from 'react';
import { useNexusStore } from '../../store/agentStore';

export function LoginPage() {
  const navigate = useNexusStore((s) => s.navigate);
  const setUser = useNexusStore((s) => s.setUser);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize Google Sign-In SDK
  useEffect(() => {
    // Check if GIS script is already loaded, otherwise initialize
    const initGoogle = () => {
      try {
        if (typeof window !== 'undefined' && (window as any).google) {
          (window as any).google.accounts.id.initialize({
            client_id: '537381825142-mockclient.apps.googleusercontent.com', // Replace with your cloud client id
            callback: handleGoogleResponse,
            auto_select: false,
            cancel_on_tap_outside: true,
          });

          (window as any).google.accounts.id.renderButton(
            document.getElementById('google-btn-container'),
            {
              theme: 'filled_black',
              size: 'large',
              width: 320,
              text: 'signin_with',
              shape: 'pill',
            }
          );
        }
      } catch (err) {
        console.warn('Google Identity Services SDK could not be initialized:', err);
      }
    };

    // If script isn't loaded yet, try initializing after a short delay
    const delay = setTimeout(initGoogle, 1000);
    return () => clearTimeout(delay);
  }, []);

  const handleGoogleResponse = async (response: any) => {
    setLoading(true);
    setError(null);
    try {
      const credential = response.credential;
      if (!credential) {
        throw new Error('No auth credentials returned from Google popup.');
      }

      // Secure backend validation request
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: credential }),
      });

      if (!res.ok) {
        throw new Error('Google Cloud validation failed. Check backend credentials.');
      }

      const session = await res.json();
      setUser({
        name: session.user.name,
        email: session.user.email,
        picture: session.user.picture || 'https://www.gravatar.com/avatar/?d=mp',
      });
      navigate('ide');
    } catch (err: any) {
      console.error('Authentication error:', err);
      setError(err.message || 'Auth verification failed. Redirecting to mock session...');
      // Self-correcting developer fallback: login with mock session on local/offline failure
      setTimeout(handleQuickDevBypass, 1500);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickDevBypass = () => {
    setLoading(true);
    setTimeout(() => {
      setUser({
        name: 'Nexus Developer',
        email: 'developer@nexusswarm.gcp',
        picture: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=80&h=80',
      });
      navigate('ide');
      setLoading(false);
    }, 800);
  };

  return (
    <div className="page-transition min-h-screen w-screen bg-[#030303] text-white flex flex-col items-center justify-center p-8 font-sans selection:bg-[#73ffb9] selection:text-[#030303]">
      {/* Background Stark Glow */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(115,255,185,0.03),transparent_45%)] pointer-events-none" />

      {/* Main Stark Login Card */}
      <div className="ledger-card max-w-md w-full relative z-10 text-center flex flex-col items-center p-10 select-none">
        {/* Logo */}
        <div className="w-12 h-12 rounded-full border border-[#73ffb9]/30 flex items-center justify-center text-xl text-[#73ffb9] mb-6">
          ⬡
        </div>

        <h2 className="text-2xl font-bold tracking-tight text-white font-pp-neue-montreal mb-2">
          Verify Identity
        </h2>
        <p className="text-sm text-[#e5e7eb]/70 font-light max-w-xs mb-8 leading-relaxed">
          Access the autonomic software swarm console. Authenticate via Google ID to log session history.
        </p>

        {error && (
          <div className="w-full bg-[#5a1d1d]/85 text-xs text-[#f44747] p-3 rounded-lg border border-[#f44747]/30 mb-6 flex items-center gap-2 log-entry justify-center">
            <span>✗</span>
            <span>{error}</span>
          </div>
        )}

        {/* Auth Buttons */}
        <div className="w-full flex flex-col items-center gap-4">
          {/* Official Google Container */}
          <div id="google-btn-container" className="h-11 min-w-[320px] relative z-20 flex justify-center" />

          {/* Quick Bypass Ghost Button */}
          <button
            onClick={handleQuickDevBypass}
            disabled={loading}
            className="w-[320px] py-3 rounded-full border border-[#e5e7eb]/35 text-[#e5e7eb] bg-transparent hover:border-[#73ffb9] hover:text-[#73ffb9] text-xs font-semibold uppercase tracking-wider transition-all duration-300 disabled:opacity-50 mt-2"
          >
            {loading ? 'Initializing Swarm...' : '⚡ Quick Dev Bypass'}
          </button>
        </div>

        {/* Dynamic Loading Overlay */}
        {loading && (
          <div className="absolute inset-0 bg-[#030303]/90 rounded-lg flex flex-col items-center justify-center z-30">
            <div className="w-8 h-8 rounded-full border-2 border-[#e5e7eb]/10 border-t-[#73ffb9] animate-spin mb-4" />
            <span className="text-xs text-[#73ffb9] font-mono tracking-widest uppercase">Connecting Swarm...</span>
          </div>
        )}
      </div>

      {/* Back to intro link */}
      <button
        onClick={() => navigate('intro')}
        disabled={loading}
        className="absolute bottom-10 text-xs text-[#e5e7eb]/50 hover:text-[#73ffb9] transition-all duration-300 font-mono tracking-wider uppercase"
      >
        ← Back to Overview
      </button>
    </div>
  );
}
