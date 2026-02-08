"use client";

import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    console.error("ErrorBoundary caught:", error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-background">
          <div className="text-center animate-fade-in">
            <div className="mb-4 text-5xl">⚠️</div>
            <h1 className="mb-2 text-xl font-bold text-foreground">Something went wrong</h1>
            <p className="mb-6 text-sm text-muted-foreground">
              An unexpected error occurred. Please try refreshing the page.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="tap-target rounded-md bg-primary px-6 py-2 text-sm font-medium text-primary-foreground transition-default hover:bg-primary/90"
            >
              Refresh page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
