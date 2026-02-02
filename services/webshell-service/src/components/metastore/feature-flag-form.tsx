/**
 * Feature Flag Form Component
 *
 * Form for creating and editing feature flags.
 */
"use client";

import { useState, useEffect } from "react";
import { X, Plus } from "lucide-react";
import type {
  FeatureFlag,
  CreateFeatureFlagRequest,
  UpdateFeatureFlagRequest,
} from "@/types/metastore";

interface FeatureFlagFormProps {
  /** Feature flag to edit (undefined for create mode) */
  flag?: FeatureFlag;
  /** Whether the form is open */
  isOpen: boolean;
  /** Callback when form is closed */
  onClose: () => void;
  /** Callback when form is submitted */
  onSubmit: (data: CreateFeatureFlagRequest | UpdateFeatureFlagRequest) => void;
  /** Whether submission is in progress */
  isSubmitting: boolean;
}

export function FeatureFlagForm({
  flag,
  isOpen,
  onClose,
  onSubmit,
  isSubmitting,
}: FeatureFlagFormProps) {
  const isEditing = !!flag;

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [defaultValue, setDefaultValue] = useState("true");
  const [defaultValueType, setDefaultValueType] = useState<"boolean" | "string" | "number" | "json">("boolean");
  const [rolloutPercentage, setRolloutPercentage] = useState(100);
  const [tags, setTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState("");
  const [expiresAt, setExpiresAt] = useState("");

  // Reset form when flag changes
  useEffect(() => {
    if (flag) {
      setName(flag.name);
      setDescription(flag.description ?? "");
      setEnabled(flag.enabled);
      setRolloutPercentage(flag.rollout_percentage);
      setTags(flag.tags);
      setExpiresAt(flag.expires_at?.split("T")[0] ?? "");

      // Determine default value type and value
      const val = flag.default_value;
      if (typeof val === "boolean") {
        setDefaultValueType("boolean");
        setDefaultValue(val.toString());
      } else if (typeof val === "number") {
        setDefaultValueType("number");
        setDefaultValue(val.toString());
      } else if (typeof val === "object") {
        setDefaultValueType("json");
        setDefaultValue(JSON.stringify(val, null, 2));
      } else {
        setDefaultValueType("string");
        setDefaultValue(String(val));
      }
    } else {
      // Reset to defaults
      setName("");
      setDescription("");
      setEnabled(false);
      setDefaultValue("true");
      setDefaultValueType("boolean");
      setRolloutPercentage(100);
      setTags([]);
      setNewTag("");
      setExpiresAt("");
    }
  }, [flag, isOpen]);

  const handleAddTag = () => {
    if (newTag && !tags.includes(newTag)) {
      setTags([...tags, newTag]);
      setNewTag("");
    }
  };

  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter((t) => t !== tag));
  };

  const parseDefaultValue = (): boolean | string | number | Record<string, unknown> => {
    switch (defaultValueType) {
      case "boolean":
        return defaultValue === "true";
      case "number":
        return Number(defaultValue);
      case "json":
        try {
          return JSON.parse(defaultValue);
        } catch {
          return {};
        }
      default:
        return defaultValue;
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const data: CreateFeatureFlagRequest | UpdateFeatureFlagRequest = {
      ...(isEditing ? {} : { name }),
      description: description || undefined,
      enabled,
      default_value: parseDefaultValue(),
      rollout_percentage: rolloutPercentage,
      tags,
      expires_at: expiresAt ? new Date(expiresAt).toISOString() : undefined,
    };

    onSubmit(data);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">
            {isEditing ? "Edit Feature Flag" : "Create Feature Flag"}
          </h2>
          <button
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6">
          <div className="space-y-4">
            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={isEditing}
                required
                placeholder="my-feature-flag"
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
              />
              <p className="mt-1 text-xs text-gray-500">
                Unique identifier (lowercase, hyphens allowed)
              </p>
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                placeholder="Describe what this feature flag controls..."
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Enabled Toggle */}
            <div className="flex items-center justify-between">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Enabled
                </label>
                <p className="text-xs text-gray-500">
                  Toggle the feature on or off globally
                </p>
              </div>
              <button
                type="button"
                onClick={() => setEnabled(!enabled)}
                className={`relative h-6 w-11 rounded-full transition-colors ${
                  enabled ? "bg-green-500" : "bg-gray-300"
                }`}
              >
                <span
                  className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                    enabled ? "translate-x-5" : "translate-x-0.5"
                  }`}
                />
              </button>
            </div>

            {/* Default Value */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Default Value
              </label>
              <div className="mt-1 flex gap-2">
                <select
                  value={defaultValueType}
                  onChange={(e) => setDefaultValueType(e.target.value as typeof defaultValueType)}
                  className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="boolean">Boolean</option>
                  <option value="string">String</option>
                  <option value="number">Number</option>
                  <option value="json">JSON</option>
                </select>
                {defaultValueType === "boolean" ? (
                  <select
                    value={defaultValue}
                    onChange={(e) => setDefaultValue(e.target.value)}
                    className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="true">true</option>
                    <option value="false">false</option>
                  </select>
                ) : defaultValueType === "json" ? (
                  <textarea
                    value={defaultValue}
                    onChange={(e) => setDefaultValue(e.target.value)}
                    rows={3}
                    className="flex-1 font-mono rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                ) : (
                  <input
                    type={defaultValueType === "number" ? "number" : "text"}
                    value={defaultValue}
                    onChange={(e) => setDefaultValue(e.target.value)}
                    className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                )}
              </div>
            </div>

            {/* Rollout Percentage */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Rollout Percentage: {rolloutPercentage}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={rolloutPercentage}
                onChange={(e) => setRolloutPercentage(Number(e.target.value))}
                className="mt-1 w-full"
              />
              <div className="mt-1 flex justify-between text-xs text-gray-500">
                <span>0%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
            </div>

            {/* Tags */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Tags
              </label>
              <div className="mt-1 flex gap-2">
                <input
                  type="text"
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddTag();
                    }
                  }}
                  placeholder="Add tag..."
                  className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <button
                  type="button"
                  onClick={handleAddTag}
                  className="rounded-md border border-gray-300 px-3 py-2 text-sm hover:bg-gray-50"
                >
                  <Plus className="h-4 w-4" />
                </button>
              </div>
              {tags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {tags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600"
                    >
                      {tag}
                      <button
                        type="button"
                        onClick={() => handleRemoveTag(tag)}
                        className="rounded-full p-0.5 hover:bg-gray-200"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Expiration */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Expires At (Optional)
              </label>
              <input
                type="date"
                value={expiresAt}
                onChange={(e) => setExpiresAt(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Actions */}
          <div className="mt-6 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || (!isEditing && !name)}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {isSubmitting ? "Saving..." : isEditing ? "Update" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
