

#main:
#	g++ -o poly poly.cpp -lppl -lgmp -std=c++0x
	



CFLAGS = -lppl -lgmp -std=c++0x
CC = g++
SRC = poly.cpp iocontract.cpp
OBJ = $(SRC:.cpp = .o)

main: $(OBJ)
	$(CC) $(OBJ) -o poly $(CFLAGS)

clean:
	rm -f core *.o