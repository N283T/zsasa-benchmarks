CXX      ?= c++
CXXFLAGS ?= -O3 -std=c++17
FREESASA ?= ../../external/freesasa
OUT      ?= ../../external/freesasa_batch/freesasa_batch

$(OUT): freesasa_batch.cc
	mkdir -p $(dir $(OUT))
	$(CXX) $(CXXFLAGS) -I $(FREESASA)/src \
		-o $(OUT) $< \
		$(FREESASA)/src/libfreesasa.a -lpthread

clean:
	rm -f $(OUT)

.PHONY: clean
