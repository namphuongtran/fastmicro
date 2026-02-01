import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";
import checkFile from "eslint-plugin-check-file";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    plugins: {
      "check-file": checkFile,
    },
    rules: {
      // ================================================================
      // File Naming Convention Rules
      // ================================================================
      
      // Enforce kebab-case for all TypeScript/TSX files
      "check-file/filename-naming-convention": [
        "error",
        {
          // All .ts and .tsx files must be kebab-case
          "**/*.{ts,tsx}": "KEBAB_CASE",
        },
        {
          // Ignore type definition files and Next.js special files
          ignoreMiddleExtensions: true,
        },
      ],
      
      // Enforce kebab-case for folder names
      "check-file/folder-naming-convention": [
        "error",
        {
          // All folders in src should be kebab-case
          "src/**/": "KEBAB_CASE",
          // Tests folder structure
          "tests/**/": "KEBAB_CASE",
        },
      ],

      // ================================================================
      // Code Naming Convention Rules
      // ================================================================
      
      "@typescript-eslint/naming-convention": [
        "warn",
        // Interfaces: PascalCase without 'I' prefix
        {
          selector: "interface",
          format: ["PascalCase"],
          custom: {
            regex: "^I[A-Z]",
            match: false,
          },
        },
        // Type aliases: PascalCase
        {
          selector: "typeAlias",
          format: ["PascalCase"],
        },
        // Enums: PascalCase
        {
          selector: "enum",
          format: ["PascalCase"],
        },
        // Enum members: UPPER_CASE
        {
          selector: "enumMember",
          format: ["UPPER_CASE"],
        },
        // Variables: camelCase or UPPER_CASE for constants
        {
          selector: "variable",
          format: ["camelCase", "UPPER_CASE", "PascalCase"],
        },
        // Functions: camelCase (PascalCase allowed for React components)
        {
          selector: "function",
          format: ["camelCase", "PascalCase"],
        },
      ],
    },
  },
  {
    // Ignore patterns for special files that don't follow kebab-case
    ignores: [
      // Next.js special files
      "**/middleware.ts",
      "**/instrumentation.ts",
      // Config files in root
      "*.config.*",
      "*.d.ts",
    ],
  },
];

export default eslintConfig;
