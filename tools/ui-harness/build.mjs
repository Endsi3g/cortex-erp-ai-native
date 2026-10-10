// Compile les composants Vue de l'assistant (hors Desk) pour les voir dans Chromium. Voir README.md.
import esbuild from "esbuild";
import vue from "esbuild-plugin-vue3";
import path from "path";
import { fileURLToPath } from "url";

const here = path.dirname(fileURLToPath(import.meta.url));
await esbuild.build({
	absWorkingDir: here,
	entryPoints: ["./entry.js"],
	bundle: true,
	outfile: "./out/bundle.js",
	format: "iife",
	plugins: [vue()],
	define: { "process.env.NODE_ENV": '"production"', __VUE_OPTIONS_API__: "true", __VUE_PROD_DEVTOOLS__: "false" },
	nodePaths: [path.join(here, "node_modules")],
	logLevel: "info",
});
