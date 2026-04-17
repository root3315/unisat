.PHONY: lib-c lib-py goldens demo test clean

CMAKE_DIR := firmware
BUILD_DIR := firmware/build

lib-c:
	cd $(CMAKE_DIR) && cmake -B build -S .
	cmake --build $(BUILD_DIR) --target sitl_fw

lib-py:
	cd ground-station && pip install -r requirements.txt 2>/dev/null || true

goldens:
	python scripts/gen_golden_vectors.py

test:
	cd $(CMAKE_DIR) && cmake -B build -S . && cmake --build build
	ctest --test-dir $(BUILD_DIR) --output-on-failure
	cd ground-station && python -m pytest tests/test_ax25.py -v

demo: lib-c lib-py
	python scripts/demo.py

clean:
	rm -rf $(BUILD_DIR)
