import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 5173,
  },
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        augurio: resolve(__dirname, "augurio.html"),
        poblado: resolve(__dirname, "poblado.html"),
        verificar: resolve(__dirname, "verificar.html"),
        recuperar: resolve(__dirname, "recuperar.html"),
        admin: resolve(__dirname, "admin.html"),
      },
    },
  },
});
