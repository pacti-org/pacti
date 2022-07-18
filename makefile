

#main:
#	g++ -o poly poly.cpp -lppl -lgmp -std=c++0x
	



CFLAGS = -lppl -lgmp -std=c++0x -fpermissive
CC = g++
SRC = contracttool.cpp iocontract.cpp
OBJ = $(SRC:.cpp = .o)

main: $(OBJ)
	$(CC) $(OBJ) -o contracttool $(CFLAGS)

poly:
	g++ -o poly poly.cpp -lppl -lgmp -std=c++0x

clean:
	rm -f core *.o