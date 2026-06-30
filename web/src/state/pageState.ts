import { Dispatch, SetStateAction, useState } from 'react';

const pageState = new Map<string, unknown>();

export function useCachedState<T>(
  key: string,
  initialValue: T | (() => T),
): readonly [T, Dispatch<SetStateAction<T>>] {
  const [value, setValue] = useState<T>(() => {
    if (pageState.has(key)) return pageState.get(key) as T;
    return initialValue instanceof Function ? initialValue() : initialValue;
  });

  const setCachedValue: Dispatch<SetStateAction<T>> = (nextValue) => {
    setValue((currentValue) => {
      const resolvedValue =
        nextValue instanceof Function ? nextValue(currentValue) : nextValue;
      pageState.set(key, resolvedValue);
      return resolvedValue;
    });
  };

  return [value, setCachedValue] as const;
}
