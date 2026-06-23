import type { AppProps } from "next/app";
import {useState} from "react";
import {
    QueryClient,
    QueryClientProvider,
  } from '@tanstack/react-query';
// import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import "./../global.css";

export default function App({ Component, pageProps }: AppProps) {
    const queryClient = new QueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      {/* {queryClient && <ReactQueryDevtools client={queryClient} initialIsOpen={false} />} */}
      <Component {...pageProps} />
    </QueryClientProvider>
  );
}
