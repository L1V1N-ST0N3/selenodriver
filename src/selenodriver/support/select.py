from __future__ import annotations

from typing import Any

from selenodriver.element import WebElement


class Select:
    def __init__(self, webelement: WebElement):
        if webelement.tag_name.lower() != "select":
            raise ValueError("Select only works on <select> elements")
        self._el = webelement
        self.is_multiple = bool(webelement.get_attribute("multiple"))

    @property
    def options(self) -> list[dict[str, Any]]:
        script = """
        (el) => Array.from(el.options).map((option, index) => ({
          index,
          text: option.text,
          value: option.value,
          selected: option.selected,
          disabled: option.disabled
        }))
        """
        return self._el._runner.run(self._el.raw.apply(script, return_by_value=True)) or []

    @property
    def all_selected_options(self) -> list[dict[str, Any]]:
        return [option for option in self.options if option.get("selected")]

    @property
    def first_selected_option(self) -> dict[str, Any]:
        selected = self.all_selected_options
        if not selected:
            raise ValueError("No option is selected")
        return selected[0]

    def select_by_value(self, value: str) -> None:
        self._select(f"value", value)

    def select_by_visible_text(self, text: str) -> None:
        self._select("text", text)

    def select_by_index(self, index: int) -> None:
        self._select("index", int(index))

    def deselect_all(self) -> None:
        if not self.is_multiple:
            raise NotImplementedError("You may only deselect all options of a multi-select")
        self._run_select_script("Array.from(el.options).forEach(option => option.selected = false);")

    def deselect_by_value(self, value: str) -> None:
        self._deselect("value", value)

    def deselect_by_visible_text(self, text: str) -> None:
        self._deselect("text", text)

    def deselect_by_index(self, index: int) -> None:
        self._deselect("index", int(index))

    def _select(self, field: str, value: Any) -> None:
        script = f"""
        const option = Array.from(el.options).find((option, index) =>
          {self._condition(field, value)}
        );
        if (!option) throw new Error('Cannot locate option');
        option.selected = true;
        if (!el.multiple) {{
          Array.from(el.options).forEach(other => {{
            if (other !== option) other.selected = false;
          }});
        }}
        """
        self._run_select_script(script)

    def _deselect(self, field: str, value: Any) -> None:
        if not self.is_multiple:
            raise NotImplementedError("You may only deselect options of a multi-select")
        script = f"""
        const option = Array.from(el.options).find((option, index) =>
          {self._condition(field, value)}
        );
        if (!option) throw new Error('Cannot locate option');
        option.selected = false;
        """
        self._run_select_script(script)

    def _run_select_script(self, body: str) -> None:
        script = f"""
        (el) => {{
          {body}
          el.dispatchEvent(new Event('input', {{ bubbles: true }}));
          el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
        """
        self._el._runner.run(self._el.raw.apply(script, return_by_value=True))

    def _condition(self, field: str, value: Any) -> str:
        if field == "index":
            return f"index === {int(value)}"
        if field == "text":
            return f"option.text === {value!r}"
        return f"option.value === {value!r}"
